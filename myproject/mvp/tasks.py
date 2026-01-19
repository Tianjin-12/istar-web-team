from celery import shared_task, chord
from celery.result import AsyncResult
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Order, Notification
from .redis_client import get_redis_client
import json


@shared_task
def schedule_order_processing():
    """凌晨0点触发：去重订单并分发处理任务"""
    redis_client = get_redis_client()

    orders = Order.objects.filter(status='pending').order_by('-created_at')

    seen = set()
    master_orders = []
    mapping = {}

    for order in orders:
        key = (order.keyword, order.brand)
        if key not in seen:
            seen.add(key)
            master_orders.append(order)
            mapping[order.id] = []
        else:
            master_id = next(o.id for o in master_orders if (o.keyword, o.brand) == key)
            mapping[master_id].append(order.id)

    for master_id, duplicate_ids in mapping.items():
        if duplicate_ids:
            redis_key = f"order_mapping:{master_id}"
            redis_client.set(redis_key, json.dumps(duplicate_ids), ex=86400)

    header = [process_order.s(order.id) for order in master_orders]
    callback = collect_and_save_results.s()
    chord(header)(callback)

    return f"已启动 {len(master_orders)} 个处理任务"


@shared_task(bind=True, time_limit=1200)
def process_order(self, order_id):
    """处理单个订单（20分钟超时）"""
    order = Order.objects.get(id=order_id)

    order.status = 'processing'
    order.task_id = self.request.id
    order.save()

    try:
        result_data = {
            "order_id": order_id,
            "keyword": order.keyword,
            "brand": order.brand,
            "status": "success",
        }

        order.status = 'completed'
        order.save()

        return result_data

    except Exception as e:
        order.status = 'failed'
        order.save()
        return {
            "order_id": order_id,
            "status": "failed",
            "error": str(e)
        }


@shared_task
def collect_and_save_results(results):
    """chord回调：收集结果并同步重复订单状态"""
    redis_client = get_redis_client()

    orders_to_update = []

    for result in results:
        order_id = result['order_id']
        status = result['status']

        redis_key = f"order_mapping:{order_id}"
        duplicate_ids = redis_client.get(redis_key)

        if duplicate_ids:
            duplicate_ids = json.loads(duplicate_ids)

            for dup_id in duplicate_ids:
                try:
                    order = Order.objects.get(id=dup_id)
                    if status == "success":
                        order.status = 'completed'
                    else:
                        order.status = 'failed'
                    orders_to_update.append(order)
                except Order.DoesNotExist:
                    pass

            redis_client.delete(redis_key)

    if orders_to_update:
        Order.objects.bulk_update(orders_to_update, ['status'])

    return f"已同步 {len(orders_to_update)} 个重复订单状态"


@shared_task
def cleanup_backend():
    """凌晨4点触发：清理未完成任务和缓存"""
    processing_orders = Order.objects.filter(status='processing')
    count = processing_orders.update(status='failed')

    from celery import current_app
    inspect = current_app.control.inspect()
    active_tasks = inspect.active()

    if active_tasks:
        for worker_name, tasks in active_tasks.items():
            for task in tasks:
                AsyncResult(task['id']).revoke(terminate=False)

    redis_client = get_redis_client()
    mapping_keys = redis_client.keys("order_mapping:*")
    if mapping_keys:
        redis_client.delete(*mapping_keys)

    return f"已标记 {count} 个处理中的订单为失败，并清理任务队列"


@shared_task
def send_notification(user_id, message, order_id=None):
    """发送通知的异步任务"""
    try:
        user = User.objects.get(id=user_id)

        order = None
        if order_id:
            order = Order.objects.get(id=order_id)

        notification = Notification.objects.create(
            user=user,
            order=order,
            message=message
        )

        return f"已向用户 {user_id} 发送通知: {message}"

    except User.DoesNotExist:
        return f"用户 {user_id} 不存在"
    except Order.DoesNotExist:
        return f"订单 {order_id} 不存在"
    except Exception as e:
        return f"发送通知时出错: {str(e)}"
