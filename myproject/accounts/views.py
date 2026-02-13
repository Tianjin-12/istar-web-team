from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .forms import LoginForm, RegisterForm
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
import random
from .models import EmailVerificationCode, UserProfile
import secrets
from django.urls import reverse

def loginView(request):
  """处理用户登录"""
  if request.user.is_authenticated:
    return redirect('accounts:profile')

  if request.method == 'POST':
    form = LoginForm(request, data=request.POST)
    if form.is_valid():
      user = form.get_user()
      login(request, user)

      nextUrl = request.GET.get('next','dashboard/brand/')
      import time
      return redirect(f"/?login_success=true&username={user.username}&timestamp={int(time.time())}")
  else:
    form = LoginForm(request)

  return render(request, 'accounts/login.html', {'form': form})


def registerView(request):
  """处理用户注册，注册后自动登录"""
  if request.user.is_authenticated:
    return redirect('accounts:profile')

  if request.method == 'POST':
    form = RegisterForm(request.POST)
    if form.is_valid():
      user = form.save()

      authenticatedUser = authenticate(
        username=form.cleaned_data['username'],
        password=form.cleaned_data['password1']
      )
      if authenticatedUser:
        login(request, authenticatedUser)

        import time
        response = redirect(f"/?register_success=true&username={user.username}&timestamp={int(time.time())}")
        return response
  else:
    form = RegisterForm()

  return render(request, 'accounts/register.html', {'form': form})


@login_required
def logoutView(request):
  """处理退出登录"""
  logout(request)
  messages.success(request, '已成功退出登录')
  return redirect('/?logout_success=true')


@login_required
def profileView(request):
  """用户个人中心"""
  return render(request, 'accounts/profile.html', {'user': request.user})


@csrf_exempt
def apiAuthCheck(request):
  """API：检查当前登录状态"""
  if request.user.is_authenticated:
    return JsonResponse({
      'authenticated': True,
      'username': request.user.username,
      'email': request.user.email,
      'user_id': request.user.id
    })
  return JsonResponse({
    'authenticated': False,
    'username': None,
    'email': None,
    'user_id': None
  })


@csrf_exempt
@login_required
def apiLogout(request):
  """API：退出登录（供 Dash 应用调用）"""
  logout(request)
  response = JsonResponse({'success': True, 'message': '已成功退出登录'})
  response.delete_cookie('sessionid')
  return response


def emailCodeResetPasswordView(request):
    """通过邮箱验证码重置密码（预留）"""
    pass


@csrf_exempt
def send_verification_code(request):
    """发送验证码"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持 POST 请求'})
    
    email = request.POST.get('email', '').strip()
    code_type = request.POST.get('code_type', 'register').strip()
    
    if not email:
        return JsonResponse({'success': False, 'message': '请输入邮箱'})
    
    # 验证 code_type
    valid_code_types = ['register', 'reset_password']
    if code_type not in valid_code_types:
        return JsonResponse({'success': False, 'message': '无效的验证码类型'})
    
    # 验证邮箱格式
    from django.core.validators import validate_email
    try:
        validate_email(email)
    except:
        return JsonResponse({'success': False, 'message': '邮箱格式不正确'})
    
    # 如果是重置密码，检查邮箱是否已注册
    if code_type == 'reset_password':
        if not User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': '该邮箱未注册'})
    
    # 如果是注册，检查邮箱是否已存在
    if code_type == 'register':
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': '该邮箱已注册，请直接登录或使用密码重置功能'})
    
    # 获取客户端IP
    ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    # 频次限制1：1分钟1邮箱1次（缓存）
    cache_key_email_1min = f'verify_code_{email}_1min_{code_type}'
    if cache.get(cache_key_email_1min):
        return JsonResponse({'success': False, 'message': '1分钟内只能发送1次'})
    
    # 频次限制2：1分钟1IP1次（缓存）
    cache_key_ip_1min = f'verify_code_{ip}_1min_{code_type}'
    if cache.get(cache_key_ip_1min):
        return JsonResponse({'success': False, 'message': '操作过于频繁，请稍后再试'})
    
    # 频次限制3：1小时1IP最多20条（缓存计数器）
    cache_key_ip_1hour = f'verify_code_{ip}_1hour_count_{code_type}'
    ip_count = cache.get(cache_key_ip_1hour, 0)
    if ip_count >= 20:
        return JsonResponse({'success': False, 'message': '该IP 1小时内发送次数已达上限（20次）'})
    
    # 频次限制4：1分钟1邮箱1次（数据库检查，作为第二道防线）
    one_minute_ago = timezone.now() - timedelta(minutes=1)
    if EmailVerificationCode.objects.filter(
        email=email,
        code_type=code_type,
        created_at__gte=one_minute_ago
    ).exists():
        return JsonResponse({'success': False, 'message': '1分钟内只能发送1次'})
    
    # 生成4位数字验证码
    code = str(random.randint(1000, 9999))
    
    # 保存验证码到数据库
    EmailVerificationCode.objects.create(
        email=email,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=10),
        ip_address=ip,
        code_type=code_type
    )
    
    # 设置缓存限制
    cache.set(cache_key_email_1min, 'sent', 60)  # 1分钟
    cache.set(cache_key_ip_1min, 'sent', 60)  # 1分钟
    cache.set(cache_key_ip_1hour, ip_count + 1, 3600)  # 1小时，递增计数
    
    # 根据code_type发送不同的邮件
    try:
        from django.conf import settings
        if code_type == 'register':
            subject = '【品牌AI可见度】注册验证码'
            message = f'您的注册验证码是：{code}，10分钟内有效。'
        else:
            subject = '【品牌AI可见度】密码重置验证码'
            message = f'您的密码重置验证码是：{code}，10分钟内有效。如非本人操作，请忽略此邮件。'
        
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            recipient_list=[email],
        )
        return JsonResponse({'success': True, 'message': '验证码已发送'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'发送失败，请重试：{str(e)}'})


def register_with_code(request):
    """邮箱验证码注册"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持 POST 请求'})
    
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    code = request.POST.get('code', '').strip()
    password1 = request.POST.get('password1', '').strip()
    password2 = request.POST.get('password2', '').strip()
    
    # 验证用户名长度（2-8字符）
    if len(username) < 2 or len(username) > 8:
        return JsonResponse({'success': False, 'message': '用户名长度必须在2-8个字符之间'})
    
    # 验证密码
    if password1 != password2:
        return JsonResponse({'success': False, 'message': '两次输入的密码不一致'})
    
    # 验证验证码
    try:
        verify_code = EmailVerificationCode.objects.get(
            email=email,
            code=code,
            code_type='register',
            is_used=False
        )

        if verify_code.is_expired():
            return JsonResponse({'success': False, 'message': '验证码已过期，请重新获取'})
    except EmailVerificationCode.DoesNotExist:
        return JsonResponse({'success': False, 'message': '验证码错误'})
    
    # 检查邮箱是否已存在
    if User.objects.filter(email=email).exists():
        return JsonResponse({'success': False, 'message': f'该邮箱已注册。如需重新注册，请访问<a href="{reverse('accounts:deregister_and_reregister')}?email={email}">重新注册</a>'})
    
    # 创建用户
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password1
    )
    
    # 标记验证码已使用
    verify_code.is_used = True
    verify_code.save()
    
    # 创建用户档案
    UserProfile.objects.create(user=user)
    
    return JsonResponse({'success': True, 'message': '注册成功'})


def reset_password_with_code(request):
    """通过验证码重置密码"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持 POST 请求'})
    
    email = request.POST.get('email', '').strip()
    code = request.POST.get('code', '').strip()
    new_password = request.POST.get('new_password', '').strip()
    
    # 验证验证码
    try:
        verify_code = EmailVerificationCode.objects.get(
            email=email,
            code=code,
            code_type='reset_password',
            is_used=False
        )

        if verify_code.is_expired():
            return JsonResponse({'success': False, 'message': '验证码已过期，请重新获取'})
    except EmailVerificationCode.DoesNotExist:
        return JsonResponse({'success': False, 'message': '验证码错误'})
    
    # 获取用户
    try:
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        # 标记验证码已使用
        verify_code.is_used = True
        verify_code.save()

        return JsonResponse({'success': True, 'message': '密码重置成功'})
    except User.DoesNotExist:
        return JsonResponse({'success': False, "message": "该邮箱未注册"})


def deregister_and_reregister(request):
    """重新注册（邮箱验证后删除旧账号）"""
    if request.method != 'POST':
        return render(request, 'accounts/deregister.html', {'email': request.GET.get('email', '')})
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        code = request.POST.get('code', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        # 验证用户名长度（2-8字符）
        if len(username) < 2 or len(username) > 8:
            return render(request, 'accounts/deregister.html', {
                'error': '用户名长度必须在2-8个字符之间'
            })
        
        # 验证验证码
        try:
            verify_code = EmailVerificationCode.objects.get(
                email=email,
                code=code,
                code_type='register',
                is_used=False
            )

            if verify_code.is_expired():
                return render(request, 'accounts/deregister.html', {
                    'error': '验证码已过期，请重新获取'
                })
        except EmailVerificationCode.DoesNotExist:
            return render(request, 'accounts/deregister.html', {
                'error': '验证码错误'
            })
        
        # 删除旧账号
        User.objects.filter(email=email).delete()
        
        # 创建新账号
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # 标记验证码已使用
        verify_code.is_used = True
        verify_code.save()
        
        # 创建用户档案
        UserProfile.objects.create(user=user)
        
        # 重新注册成功，跳转到登录页
        return redirect(f'/accounts/login/?register_success=true&username={username}')
