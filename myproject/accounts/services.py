import random
import string
from django.utils import timezone
from datetime import timedelta
from .models import EmailVerificationCode


class EmailCodeService:
    """邮箱验证码服务（预留）"""
    
    @staticmethod
    def generate_code():
        """生成 6 位随机验证码"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def create_and_send_code(email):
        """创建并发送验证码"""
        code = EmailCodeService.generate_code()
        
        # 保存到数据库
        EmailVerificationCode.objects.create(
            email=email,
            code=code
        )
        
        # TODO: 发送邮件
        # send_mail('验证码', f'您的验证码是：{code}', from_email, [email])
        
        return code
    
    @staticmethod
    def verify_code(email, code):
        """验证验证码是否正确"""
        # 查找 10 分钟内未使用的验证码
        time_threshold = timezone.now() - timedelta(minutes=10)
        verification_code = EmailVerificationCode.objects.filter(
            email=email,
            code=code,
            is_used=False,
            created_at__gte=time_threshold
        ).first()
        
        if verification_code:
            # 标记为已使用
            verification_code.is_used = True
            verification_code.save()
            return True
        
        return False
