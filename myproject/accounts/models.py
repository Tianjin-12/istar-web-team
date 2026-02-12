from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class EmailVerificationCode(models.Model):
    """邮箱验证码模型"""
    CODE_TYPE_CHOICES = [
        ('register', '注册验证码'),
        ('reset_password', '重置密码验证码'),
    ]

    email = models.EmailField(verbose_name='邮箱')
    code = models.CharField(max_length=4, verbose_name='验证码')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    expires_at = models.DateTimeField(default=timezone.now, verbose_name='过期时间')
    ip_address = models.GenericIPAddressField(default='127.0.0.1', verbose_name='IP地址')
    code_type = models.CharField(
        max_length=20,
        choices=CODE_TYPE_CHOICES,
        default='register',
        verbose_name='验证码类型'
    )
    is_used = models.BooleanField(default=False, verbose_name='是否已使用')

    class Meta:
        verbose_name = '邮箱验证码'
        verbose_name_plural = '邮箱验证码'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'code_type']),
            models.Index(fields=['ip_address', 'created_at']),
        ]

    def __str__(self):
        return f'{self.email} - {self.code} ({self.code_type})'

    def is_expired(self):
        """检查验证码是否过期"""
        return timezone.now() > self.expires_at


class UserProfile(models.Model):
    """用户档案"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户')
    remember_me_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name='记住我Token'
    )
    remember_me_expires = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='记住我过期时间'
    )

    class Meta:
        verbose_name = '用户档案'
        verbose_name_plural = '用户档案'

    def __str__(self):
        return f'{self.user.username} 的档案'
