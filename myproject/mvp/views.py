from django_plotly_dash.models import StatelessApp
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from .models import Mention_percentage
from .serializers import Mention_percentageSerializer
import json
import os
from django.conf import settings
from datetime import datetime,timedelta
from django.core.cache import cache
from django.shortcuts import render, redirect
from .models import Order
from functools import wraps
from urllib.parse import urlparse, urlencode
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max



def login_required_new_tab(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    自定义的login_required装饰器，当用户未登录时在新标签页中打开登录页面
    登录成功后自动刷新原始页面
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # 用户未登录，返回一个在新标签页中打开登录页面的响应
            path = request.build_absolute_uri()
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)
            
            # 构建带有next参数的登录URL
            query_params = {redirect_field_name: path}
            login_url_with_next = f"{resolved_login_url}?{urlencode(query_params)}"
            
            # 返回一个包含JavaScript的响应，在新标签页中打开登录页面并监听登录状态
            with open('/var/www/myproject/mvp/listening.html', encoding='utf-8') as f:
                html = f.read()
            return HttpResponse(html)
        return _wrapper_view
    if function:
        return decorator(function)
    return decorator


@login_required_new_tab
def order_list(request):
    """显示当前用户的订单列表"""
    orders = Order.objects.filter(
        user=request.user
    ).select_related('user').order_by('-created_at')
    return render(request, 'mvp/order_list.html', {'orders': orders})

@login_required_new_tab
def create_order(request):
    """创建新订单"""
    if request.method == 'POST':
        keyword = request.POST.get('keyword', '').strip()
        brand = request.POST.get('brand', '').strip()

        if not keyword or not brand:
            return JsonResponse({
                'success': False,
                'message': '请提供关键词和品牌词'
            })

        existing_order = Order.objects.filter(
            user=request.user,
            keyword__iexact=keyword,
            brand__iexact=brand
        ).first()

        if existing_order:
            return JsonResponse({
                'success': False,
                'message': f'您已经创建过品牌"{brand}"和关键词"{keyword}"的订单'
            })

        order = Order.objects.create(
            user=request.user,
            keyword=keyword,
            brand=brand,
            status='pending'
        )

        return JsonResponse({
            'success': True,
            'message': '订单创建成功',
            'order_id': order.id
        })

    prefilled_brand = request.session.pop('prefilled_brand', '')
    prefilled_keyword = request.session.pop('prefilled_keyword', '')
    return render(request, 'mvp/create_order.html', {
        'prefilled_brand': prefilled_brand,
        'prefilled_keyword': prefilled_keyword
    })


class Mention_percentageViewSet(viewsets.ModelViewSet):
    """提及百分比API视图集"""
    queryset = Mention_percentage.objects.all()
    serializer_class = Mention_percentageSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset
    
# API端点，用于获取仪表盘数据
@csrf_exempt
def dashboard_data_api(request):
    if request.method == 'GET':
        try:
            brand_name = request.GET.get('brand_name', '')
            keyword = request.GET.get('keyword', '')
            link = request.GET.get('link','')

            days = int(request.GET.get('days', 60))
              # 默认获取60天的数据   
            config_path = os.path.join(settings.BASE_DIR, 'brand_config.json')
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"brand_name":brand_name,"keyword":keyword,"link":link},f,ensure_ascii=False)
            cache_key = f"dashboard_data_{brand_name}_{keyword}_{days}"
            # 尝试从缓存中获取数据
            cached_data = cache.get(cache_key)
            if cached_data:
                return JsonResponse({'data': cached_data,  'from_cache': True})
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            # 检查Order表中是否有该(brand, keyword)组合
            has_order = Order.objects.filter(
                keyword__icontains=keyword,
                brand__icontains=brand_name
            ).exists()
            if not has_order:
                # 如果没有订单，返回特殊标记
                return JsonResponse({
                    'no_order': True,
                    'brand_name': brand_name,
                    'keyword': keyword,
                    'status': 'no_order'
                })
            # 查询提及数据
            mention_query = Mention_percentage.objects.filter(
                created_at__range=[start_date, end_date],keyword_name__icontains=keyword
            )
            data = {
                'r_brand_amount': list(mention_query.values_list('r_brand_amount', flat=True)),
                'nr_brand_amount': list(mention_query.values_list('nr_brand_amount', flat=True)),
                'link_amount': list(mention_query.values_list("link_amount", flat=True)),
                "keyword_name": list(mention_query.values_list('keyword_name', flat=True)),
                "brand_name": list(mention_query.values_list('brand_name', flat=True)),
                "created_at": list(mention_query.values_list('created_at', flat=True)),
                    }
            return JsonResponse({'data': data, 'status': 'success'})
        
        except Exception as e:
            return JsonResponse({'error': str(e), 'status': 'error'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method', 'status': 'error'}, status=405)

# 托管Dash应用
def dashboard_view(request):
    # 确保Dash应用已注册
    try:
        # 尝试获取Dash应用
        dash_app = StatelessApp.objects.get(slug='DashboardApp')
    except StatelessApp.DoesNotExist:
        # 如果不存在，创建一个
        dash_app = StatelessApp.objects.create(
            slug='DashboardApp',
            app_name='DashboardApp'
        )
    
    return render(request, 'mvp/dashboard.html')

from .models import Notification
@login_required_new_tab
def redirect_to_create_order(request):
    """从Dash应用重定向到订单创建页面，并预填品牌和关键词"""
    brand_name = request.GET.get('brand_name', '')
    keyword_name = request.GET.get('keyword_name', '')

    # 将品牌和关键词保存到session中，以便在创建订单页面使用
    request.session['prefilled_brand'] = brand_name
    request.session['prefilled_keyword'] = keyword_name

    # 重定向到订单创建页面
    return redirect('mvp:create_order')

@login_required_new_tab
def notification_list(request):
    """显示用户的所有通知"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # 标记所有通知为已读
    notifications.update(is_read=True)
    
    return render(request, 'mvp/notification_list.html', {'notifications': notifications})

@login_required_new_tab
def unread_notification_count(request):
    """获取未读通知数量"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})

@login_required_new_tab
def mark_notification_read(request, notification_id):
  """
  标记通知为已读
  """
  try:
    notification = Notification.objects.get(id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})
  except Notification.DoesNotExist:
    return JsonResponse({'success': False, 'error': '通知不存在'})


@csrf_exempt
@login_required
def notification_list_api(request):
  """返回 JSON 格式的通知列表"""
  notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
  data = [
    {
      'id': n.id,
      'message': n.message,
      'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S'),
      'is_read': n.is_read,
      'order_id': n.order.id if n.order else None
    }
    for n in notifications
  ]
  return JsonResponse({'data': data}, safe=False)