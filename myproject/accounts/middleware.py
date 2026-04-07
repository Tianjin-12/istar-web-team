# accounts/middleware.py

import secrets
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import login
from django.utils import timezone
from .models import UserProfile


def _rotate_token():
    """生成新的 remember_me token"""
    return secrets.token_urlsafe(48)


class RememberMeMiddleware:
    """记住我中间件"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        remember_token = request.COOKIES.get('remember_me_token')

        if remember_token and not request.user.is_authenticated:
            try:
                profile = UserProfile.objects.select_related('user').get(
                    remember_me_token=remember_token,
                    remember_me_expires__gt=timezone.now(),
                    user__is_active=True,
                )
                new_token = _rotate_token()
                profile.remember_me_token = new_token
                profile.save(update_fields=['remember_me_token'])
                login(request, profile.user)
                response = self.get_response(request)
                max_age = 30 * 24 * 3600
                response.set_cookie(
                    'remember_me_token',
                    new_token,
                    max_age=max_age,
                    httponly=True,
                    secure=request.is_secure(),
                    samesite='Lax',
                )
                return response
            except UserProfile.DoesNotExist:
                pass

        return self.get_response(request)
