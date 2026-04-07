from celery import shared_task, chord, chain
from celery.result import AsyncResult
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from django.db import transaction
from .models import (
    Order,
    Notification,
    TaskLog,
    ZhihuQuestion,
    QuestionBank,
    AIAnswer,
    QuestionScore,
)
from .redis_client import get_redis_client
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ========================================
# 阶段1: 订单分组(每天00:00触发)
# ========================================


@shared_task(name="mvp.schedule_order_processing")
def schedule_order_processing():
    try:
        pending_orders = Order.objects.filter(status="pending")

        # 按关键词分组
        keyword_groups = {}
        for order in pending_orders:
            keyword = order.keyword
            if keyword not in keyword_groups:
                keyword_groups[keyword] = []
            keyword_groups[keyword].append(order)

        # 对每个关键词启动任务链
        total_tasks = 0
        for keyword, orders in keyword_groups.items():
            try:
                # 启动任务链
                chain(
                    search_questions.s(keyword),
                    build_question_bank.s(keyword),
                    collect_ai_answers.s(keyword),
                    score_questions.s(keyword),
                    analyze_orders_by_keyword.s(keyword, [o.id for o in orders]),
                ).apply_async()

                # 更新订单状态（只有任务链启动成功才更新）
                Order.objects.filter(id__in=[o.id for o in orders]).update(
                    status="processing", current_stage="searching"
                )

                total_tasks += 1

            except Exception as e:
                # 单个关键词任务启动失败，不影响其他关键词
                print(f"关键词 {keyword} 任务启动失败: {str(e)}")
                continue

        return f"已启动 {total_tasks} 个关键词的任务链"

    except Exception as e:
        logger.error(f"schedule_order_processing 执行失败: {str(e)}")
        return "任务启动失败，请联系管理员"


# ========================================
# 阶段3: 搜索知乎问题(7天缓存)
# ========================================


@shared_task(name="mvp.search_questions")
def search_questions(keyword):
    """搜索知乎问题并保存到数据库"""
    task_log = None
    try:
        from .searching import searching_with_db

        task_log = TaskLog.objects.create(
            task_type="search_questions", status="running", started_at=timezone.now()
        )

        questions = searching_with_db(keyword, use_cache=True)

        task_log.status = "completed"
        task_log.completed_at = timezone.now()
        task_log.duration = int(
            (task_log.completed_at - task_log.started_at).total_seconds()
        )
        task_log.save()

        return {"status": "success", "count": len(questions)}

    except Exception as e:
        if task_log:
            task_log.status = "failed"
            task_log.error_message = str(e)
            task_log.completed_at = timezone.now()
            task_log.save()
        raise e


# ========================================
# 阶段4: 构建问题库(7天缓存)
# ========================================


@shared_task(name="mvp.build_question_bank")
def build_question_bank(keyword):
    """构建问题库并保存到数据库"""
    task_log = None
    try:
        from .question_bank import build_bank_with_db

        task_log = TaskLog.objects.create(
            task_type="build_question_bank", status="running", started_at=timezone.now()
        )

        questions = build_bank_with_db(keyword)

        task_log.status = "completed"
        task_log.completed_at = timezone.now()
        task_log.duration = int(
            (task_log.completed_at - task_log.started_at).total_seconds()
        )
        task_log.save()

        return {"status": "success", "count": len(questions)}

    except Exception as e:
        if task_log:
            task_log.status = "failed"
            task_log.error_message = str(e)
            task_log.completed_at = timezone.now()
            task_log.save()
        raise e


# ========================================
# 阶段5: 收集AI回答(1天缓存)
# ========================================


@shared_task(name="mvp.collect_ai_answers")
def collect_ai_answers(keyword):
    """收集AI回答并保存到数据库（多账号并行版本）"""
    import asyncio
    import sys as _sys

    task_log = None
    try:
        from .crabbing_parallel import collect_answers_parallel_async

        if _sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        task_log = TaskLog.objects.create(
            task_type="collect_ai_answers", status="running", started_at=timezone.now()
        )

        result = asyncio.run(collect_answers_parallel_async(keyword))

        task_log.completed_at = timezone.now()
        task_log.duration = int(
            (task_log.completed_at - task_log.started_at).total_seconds()
        )
        if result == True:
            task_log.status = "completed"
            task_log.save()
        return {"status": "success"}

    except Exception as e:
        if task_log:
            task_log.status = "failed"
            task_log.error_message = str(e)
            task_log.completed_at = timezone.now()
            task_log.save()
        raise e


# ========================================
# 阶段6: 问题评分(1天缓存)
# ========================================


@shared_task(name="mvp.score_questions")
def score_questions(keyword):
    """对问题进行评分并保存到数据库"""
    task_log = None
    try:
        from .question_bank import score_questions_with_db

        task_log = TaskLog.objects.create(
            task_type="score_questions", status="running", started_at=timezone.now()
        )

        result = score_questions_with_db(keyword)

        task_log.status = "completed"
        task_log.completed_at = timezone.now()
        task_log.duration = int(
            (task_log.completed_at - task_log.started_at).total_seconds()
        )
        task_log.save()

        return {"status": "success"}

    except Exception as e:
        if task_log:
            task_log.status = "failed"
            task_log.error_message = str(e)
            task_log.completed_at = timezone.now()
            task_log.save()
        raise e


# ========================================
# 阶段7: 批量分析订单
# ========================================


@shared_task(name="mvp.analyze_orders_by_keyword")
@transaction.atomic
def analyze_orders_by_keyword(keyword, order_ids):
    """批量分析关键词关联的所有订单"""
    from .summary import analyze_summary
    from mvp.models import Mention_percentage
    from django.utils import timezone
    from datetime import timedelta

    results = []
    # 先获取所有订单的品牌信息，避免重复查询
    orders = list(Order.objects.filter(id__in=order_ids))
    brand_set = set(order.brand for order in orders)
    # 检查每个品牌是否已有今天的分析结果
    brand_result_cache = {}
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    for brand in brand_set:
        # 查询今天或昨天的分析结果
        existing_result = (
            Mention_percentage.objects.filter(
                keyword_name=keyword, brand_name=brand, created_at__date__gte=yesterday
            )
            .order_by("-created_at")
            .first()
        )

        if existing_result:
            brand_result_cache[brand] = existing_result.id
            print(
                f"✓ 发现已有分析结果: keyword={keyword}, brand={brand}, result_id={existing_result.id}"
            )
        else:
            brand_result_cache[brand] = None
            print(f"✗ 需要新建分析结果: keyword={keyword}, brand={brand}")
    for order_id in order_ids:
        order = None
        try:
            # 获取订单
            order = Order.objects.get(id=order_id)

            # 更新订单状态
            order.current_stage = "analyzing"
            order.save()

            # 检查是否已有分析结果
            if order.brand in brand_result_cache and brand_result_cache[order.brand]:
                # ✓ 使用现有结果
                result_id = brand_result_cache[order.brand]
                is_cached = True
                print(f"订单 {order_id}: 使用缓存 result_id={result_id}")
            else:
                # ✗ 执行分析
                result_id = analyze_summary(keyword, order.brand)
                is_cached = False
                print(f"订单 {order_id}: 执行分析 result_id={result_id}")

            # 更新订单状态
            order.status = "completed"
            order.current_stage = "completed"
            order.progress_percentage = 100
            order.is_cached = is_cached
            order.save()

            # 发送通知
            send_notification.delay(
                user_id=order.user.id,
                message=f"订单 {order.id} 分析完成",
                order_id=order.id,
            )

            results.append(
                {"order_id": order_id, "status": "success", "result_id": result_id}
            )

        except Order.DoesNotExist:
            # 订单不存在
            results.append(
                {
                    "order_id": order_id,
                    "status": "failed",
                    "error": f"订单 {order_id} 不存在",
                }
            )

        except Exception as e:
            # 更新订单状态
            if order:
                order.status = "failed"
                order.last_error = str(e)
                order.save()

            results.append({"order_id": order_id, "status": "failed", "error": str(e)})

    return results


# ========================================
# 定时任务: 数据清理
# ========================================


@shared_task(name="mvp.cleanup_old_data")
def cleanup_old_data():
    """清理过期数据"""
    from django.utils import timezone

    try:
        deleted_zhihu = 0
        deleted_qb = 0
        deleted_answers = 0
        deleted_scores = 0

        # 删除7天前的知乎问题
        threshold_7d = timezone.now() - timedelta(days=7)
        try:
            deleted_zhihu = ZhihuQuestion.objects.filter(
                created_at__lt=threshold_7d
            ).delete()[0]
        except Exception as e:
            logger.error(f"清理知乎问题失败: {e}")

        # 删除7天前的问题库
        try:
            deleted_qb = QuestionBank.objects.filter(
                created_at__lt=threshold_7d
            ).delete()[0]
        except Exception as e:
            logger.error(f"清理问题库失败: {e}")

        # 删除3天前的AI回答（AILink 通过 SET_NULL 保留，不会级联删除）
        threshold_3d = timezone.now() - timedelta(days=3)
        try:
            deleted_answers = AIAnswer.objects.filter(
                created_at__lt=threshold_3d
            ).delete()[0]
        except Exception as e:
            logger.error(f"清理AI回答失败: {e}")

        # 删除3天前的评分
        try:
            deleted_scores = QuestionScore.objects.filter(
                created_at__lt=threshold_3d
            ).delete()[0]
        except Exception as e:
            logger.error(f"清理评分失败: {e}")

        # AILink 永久保留，不清理

        result = {
            "zhihu": deleted_zhihu,
            "question_bank": deleted_qb,
            "answers": deleted_answers,
            "scores": deleted_scores,
        }
        logger.info(f"数据清理完成: {result}")
        return result

    except Exception as e:
        logger.error(f"数据清理失败: {str(e)}")
        return f"数据清理失败: {str(e)}"


@shared_task(name="mvp.archive_old_data")
def archive_old_data():
    """归档任务日志(1个月)"""
    import csv
    import os
    from django.conf import settings
    from django.utils import timezone

    threshold_1m = timezone.now() - timedelta(days=30)

    # 查询1个月前的任务日志
    old_logs = TaskLog.objects.filter(started_at__lt=threshold_1m)

    # 导出为CSV
    log_dir = os.path.join(settings.BASE_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    filename = os.path.join(log_dir, f"{timezone.now().strftime('%Y-%m')}.csv")

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "id",
                "order_id",
                "task_type",
                "status",
                "retry_count",
                "error_message",
                "started_at",
                "completed_at",
                "duration",
            ]
        )

        for log in old_logs:
            writer.writerow(
                [
                    log.id,
                    log.order_id,
                    log.task_type,
                    log.status,
                    log.retry_count,
                    log.error_message,
                    log.started_at,
                    log.completed_at,
                    log.duration,
                ]
            )

    # 删除数据库记录
    count = old_logs.count()
    old_logs.delete()

    return {"archived": count, "filename": filename}


@shared_task
def cleanup_backend():
    """凌晨4点触发: 清理未完成任务和缓存"""
    try:
        processing_orders = Order.objects.filter(status="processing")
        count = processing_orders.update(status="failed")
        from celery import current_app

        inspect = current_app.control.inspect()
        active_tasks = inspect.active()
        if active_tasks:
            for worker_name, tasks in active_tasks.items():
                for task in tasks:
                    AsyncResult(task["id"]).revoke(terminate=False)
        redis_client = get_redis_client()
        if redis_client is None:
            print("警告: 无法获取 Redis 客户端，跳过缓存清理")
            return f"已标记 {count} 个处理中的订单为失败"

        mapping_keys = list(redis_client.scan_iter("order_mapping:*"))
        if mapping_keys:
            redis_client.delete(*mapping_keys)
        return f"已标记 {count} 个处理中的订单为失败，并清理任务队列"

    except Exception as e:
        print(f"cleanup_backend 执行失败: {str(e)}")
        return f"清理失败: {str(e)}"


@shared_task(name="mvp.send_notification")
def send_notification(user_id, message, order_id=None):
    """发送通知的异步任务"""
    try:
        user = User.objects.get(id=user_id)

        order = None
        if order_id:
            order = Order.objects.get(id=order_id)

        notification = Notification.objects.create(
            user=user, order=order, message=message
        )

        return f"已向用户 {user_id} 发送通知: {message}"

    except User.DoesNotExist:
        return f"用户 {user_id} 不存在"
    except Order.DoesNotExist:
        return f"订单 {order_id} 不存在"
    except Exception as e:
        return f"发送通知时出错: {str(e)}"


# ========================================
# 定时任务: 更新排行榜JSON
# ========================================


@shared_task(name="mvp.update_ranking_json")
def update_ranking_json():
    """每天05:00触发: 聚合Mention_percentage最新数据，生成ranking.json"""
    import os
    from django.conf import settings
    from django.db.models import Max

    try:
        from .models import Mention_percentage

        # 获取每个(brand_name, keyword_name)组合的最新一条记录
        latest_ids = (
            Mention_percentage.objects.values("brand_name", "keyword_name")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )

        records = Mention_percentage.objects.filter(id__in=latest_ids).order_by(
            "field_name", "-r_brand_amount"
        )

        categories = {}
        for r in records:
            field = r.field_name or "未分类"
            if field not in categories:
                categories[field] = []
            categories[field].append(
                {
                    "brand": r.brand_name,
                    "keyword": r.keyword_name,
                    "r_brand_amount": round(r.r_brand_amount, 2),
                    "high_relevance_ratio": round(r.high_relevance_ratio, 2),
                    "nr_brand_amount": round(r.nr_brand_amount, 2),
                    "link_amount": round(r.link_amount, 2),
                    "updated_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
                }
            )

        data = {
            "updated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_brands": len(records),
            "categories": categories,
        }

        json_path = os.path.join(
            os.path.join(settings.BASE_DIR, "mvp", "static"), "ranking.json"
        )
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"排行榜JSON更新完成: {len(records)} 个品牌, {len(categories)} 个行业"
        )
        return {
            "status": "success",
            "total_brands": len(records),
            "categories": len(categories),
        }

    except Exception as e:
        logger.error(f"更新排行榜JSON失败: {str(e)}")
        return {"status": "failed", "error": str(e)}
