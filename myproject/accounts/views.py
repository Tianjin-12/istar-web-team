from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .forms import LoginForm, RegisterForm
import time

def loginView(request):
  """处理用户登录"""
  if request.user.is_authenticated:
    return redirect('accounts:profile')

  if request.method == 'POST':
    form = LoginForm(request, data=request.POST)
    if form.is_valid():
      user = form.get_user()
      login(request, user)

      nextUrl = request.GET.get('next', '/')
      import time
      response = redirect(f"{nextUrl}?login_success=true&username={user.username}&timestamp={int(time.time())}")
      return response
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
  return redirect('accounts:login')


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
