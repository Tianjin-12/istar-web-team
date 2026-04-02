import os
import sys
import random
from datetime import date, timedelta
from collections import defaultdict

from django.utils import timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

import django

django.setup()

from mvp.models import AIAnswer, QuestionBank, QuestionScore, AILink, Mention_percentage
from mvp.link_classifier import (
    ensure_default_categories,
    classifyLinksBatch,
    getCategoryStats,
    getHighRelevanceRatio,
)


def _sample_answers_by_day(keyword, target_date, ratio=1.0):
    qs = AIAnswer.objects.filter(keyword=keyword, answer_date=target_date)
    all_answers = list(qs)
    if ratio >= 1.0 or len(all_answers) == 0:
        return all_answers
    sample_size = min(round(len(all_answers) * ratio), len(all_answers))
    return random.sample(all_answers, sample_size)


def analyze_summary(keyword, brand):
    try:
        ensure_default_categories()

        today = date.today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        sample_today = _sample_answers_by_day(keyword, today, 1.0)
        sample_yesterday = _sample_answers_by_day(keyword, yesterday, 0.3)
        sample_daybefore = _sample_answers_by_day(keyword, day_before, 0.15)

        all_answers = sample_today + sample_yesterday + sample_daybefore

        # 同一 question_id 在不同天可能出现多次，用第一条的文本
        answers = {}
        for ans in all_answers:
            if ans.question_id not in answers:
                answers[ans.question_id] = ans.answer_text

        total = len(answers)

        if total == 0:
            result = Mention_percentage.objects.create(
                brand_name=brand,
                keyword_name=keyword,
                field_name=keyword,
                brand_amount=0,
                r_brand_amount=0,
                nr_brand_amount=0,
                link_amount=0,
                r_link_amount=0,
                nr_link_amount=0,
                high_relevance_ratio=0,
                source_stats={},
                created_at=timezone.now(),
            )
            return result.id

        scores = {
            str(qid): score
            for qid, score in QuestionScore.objects.filter(keyword=keyword).values_list(
                "question_id", "score"
            )
        }
        # 没有评分数据时，所有问题都标记为非推荐
        if not scores:
            scores = {qid: 0 for qid in answers.keys()}

        high_ids = {qid for qid, score in scores.items() if score in [3, 4]}

        brand_count = r_brand = nr_brand = 0
        for qid, text in answers.items():
            if brand in text:
                brand_count += 1
                if qid in high_ids:
                    r_brand += 1
                else:
                    nr_brand += 1

        answer_ids = [ans.id for ans in all_answers]
        id_map = {ans.id: ans.question_id for ans in all_answers}

        # 每个 question_id 对应多个 answer_id 时，去重链接
        link_dict = defaultdict(set)
        for link in AILink.objects.filter(answer_id__in=answer_ids).values(
            "answer_id", "link_url"
        ):
            qid = id_map.get(link["answer_id"])
            if qid:
                link_dict[qid].add(link["link_url"])

        link_count = r_link = nr_link = 0
        for qid in answers.keys():
            if any(brand in link for link in link_dict.get(qid, set())):
                link_count += 1
                if qid in high_ids:
                    r_link += 1
                else:
                    nr_link += 1

        all_links = list(AILink.objects.filter(answer_id__in=answer_ids))
        raw_counts = classifyLinksBatch(all_links)
        source_stats = getCategoryStats(raw_counts)
        high_relevance_ratio = getHighRelevanceRatio(source_stats)

        result = Mention_percentage.objects.create(
            brand_name=brand,
            keyword_name=keyword,
            field_name=keyword,
            brand_amount=brand_count / total * 100,
            r_brand_amount=r_brand / total * 100,
            nr_brand_amount=nr_brand / total * 100,
            link_amount=link_count / total * 100,
            r_link_amount=r_link / total * 100,
            nr_link_amount=nr_link / total * 100,
            high_relevance_ratio=high_relevance_ratio,
            source_stats=source_stats,
            created_at=timezone.now(),
        )

        return result.id

    except Exception as e:
        raise e
