import redis
from django.conf import settings


def get_redis_client():
    """获取 Redis 连接（用于订单映射存储，db=1）"""
    # Celery result backend 也用 db=1，直接复用
    return redis.Redis.from_url(
        settings.CELERY_RESULT_BACKEND,
        decode_responses=True
    )
