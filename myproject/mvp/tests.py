from django.test import TestCase
from django.contrib.auth.models import User
from .models import Order
from .tasks import cleanup_backend
from .redis_client import get_redis_client
import json


class TaskTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.redis_client = get_redis_client()

    def tearDown(self):
        """清理测试数据"""
        redis_client = get_redis_client()
        mapping_keys = redis_client.keys("order_mapping:*")
        if mapping_keys:
            redis_client.delete(*mapping_keys)

    def test_deduplication_logic(self):
        """测试去重逻辑"""
        order1 = Order.objects.create(
            user=self.user,
            keyword='手机',
            brand='华为',
            status='pending'
        )
        order2 = Order.objects.create(
            user=self.user,
            keyword='手机',
            brand='华为',
            status='pending'
        )
        order3 = Order.objects.create(
            user=self.user,
            keyword='电脑',
            brand='联想',
            status='pending'
        )

        from django.utils import timezone
        old_date = timezone.now() - timezone.timedelta(days=1)
        order1.created_at = old_date
        order1.save()

        orders = Order.objects.filter(status='pending').order_by('-created_at')
        seen = set()
        master_orders = []

        for order in orders:
            key = (order.keyword, order.brand)
            if key not in seen:
                seen.add(key)
                master_orders.append(order)

        self.assertEqual(len(master_orders), 2)
        self.assertIn(order3, master_orders)
        self.assertIn(order2, master_orders)
        self.assertNotIn(order1, master_orders)

    def test_order_mapping_storage(self):
        """测试订单映射存储到 Redis"""
        master_order = Order.objects.create(
            user=self.user,
            keyword='测试',
            brand='品牌',
            status='pending'
        )
        duplicate_order = Order.objects.create(
            user=self.user,
            keyword='测试',
            brand='品牌',
            status='pending'
        )

        redis_key = f"order_mapping:{master_order.id}"
        mapping_data = [duplicate_order.id]

        self.redis_client.set(redis_key, json.dumps(mapping_data), ex=86400)

        stored_data = self.redis_client.get(redis_key)
        self.assertIsNotNone(stored_data)

        parsed_data = json.loads(stored_data)
        self.assertEqual(parsed_data, mapping_data)

    def test_process_order_status_update(self):
        """测试 process_order 状态更新"""
        order = Order.objects.create(
            user=self.user,
            keyword='测试',
            brand='品牌',
            status='pending'
        )

        result = process_order(order.id)

        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['order_id'], order.id)

    def test_process_order_with_duplicate_sync(self):
        """测试重复订单状态同步"""
        master_order = Order.objects.create(
            user=self.user,
            keyword='测试',
            brand='品牌',
            status='pending'
        )
        duplicate_order = Order.objects.create(
            user=self.user,
            keyword='测试',
            brand='品牌',
            status='pending'
        )

        redis_key = f"order_mapping:{master_order.id}"
        self.redis_client.set(redis_key, json.dumps([duplicate_order.id]), ex=86400)

        master_result = process_order(master_order.id)

        results = [master_result]
        collect_and_save_results(results)

        master_order.refresh_from_db()
        duplicate_order.refresh_from_db()

        self.assertEqual(master_order.status, 'completed')
        self.assertEqual(duplicate_order.status, 'completed')

    def test_cleanup_backend_marks_processing_as_failed(self):
        """测试清理任务标记 processing 为 failed"""
        order = Order.objects.create(
            user=self.user,
            keyword='测试',
            brand='品牌',
            status='processing'
        )

        cleanup_backend()

        order.refresh_from_db()
        self.assertEqual(order.status, 'failed')

    def test_cleanup_backend_clears_redis_mapping(self):
        """测试清理任务清理 Redis 映射"""
        order = Order.objects.create(
            user=self.user,
            keyword='测试',
            brand='品牌',
            status='pending'
        )

        redis_key = f"order_mapping:{order.id}"
        self.redis_client.set(redis_key, json.dumps([]), ex=86400)

        cleanup_backend()

        stored_data = self.redis_client.get(redis_key)
        self.assertIsNone(stored_data)

    def test_failed_order_sync_to_duplicates(self):
        """测试失败订单同步到重复订单"""
        master_order = Order.objects.create(
            user=self.user,
            keyword='测试',
            brand='品牌',
            status='pending'
        )
        duplicate_order = Order.objects.create(
            user=self.user,
            keyword='测试',
            brand='品牌',
            status='pending'
        )

        redis_key = f"order_mapping:{master_order.id}"
        self.redis_client.set(redis_key, json.dumps([duplicate_order.id]), ex=86400)

        failed_result = {
            "order_id": master_order.id,
            "status": "failed",
            "error": "测试错误"
        }

        collect_and_save_results([failed_result])

        master_order.refresh_from_db()
        duplicate_order.refresh_from_db()

        self.assertEqual(duplicate_order.status, 'failed')
