# accounts/middleware.py

from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import login
from django.utils import timezone
from .models import UserProfile

class RememberMeMiddleware:
    """记住我中间件"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 检查是否有"记住我"Cookie
        remember_token = request.COOKIES.get('remember_me_token')

        if remember_token and not request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(
                    remember_me_token=remember_token,
                    remember_me_expires__gt=timezone.now()
                )
                # 自动登录
                login(request, profile.user)
                return self.get_response(request)
            except UserProfile.DoesNotExist:
                pass

        response = self.get_response(request)
        return response
