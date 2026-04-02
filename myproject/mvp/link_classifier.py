import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

import django

django.setup()

from mvp.models import LinkCategory, AILink

DEFAULT_CATEGORIES = [
    {
        "name": "官方媒体",
        "relevance_level": 5,
        "domain_patterns": [
            "gov.cn",
            "xinhuanet.com",
            "people.com.cn",
            "cctv.com",
            "cctv.cn",
            "china.com.cn",
            "china.com",
            "ce.cn",
            "gmw.cn",
            "cnr.cn",
        ],
        "color": "#e74c3c",
        "order": 1,
    },
    {
        "name": "知名媒体",
        "relevance_level": 4,
        "domain_patterns": [
            "sina.com.cn",
            "sohu.com",
            "163.com",
            "qq.com",
            "ifeng.com",
            "thepaper.cn",
            "caixin.com",
            "yicai.com",
            "jiemian.com",
            "36kr.com",
            "finance.sina.com.cn",
            "news.sina.com.cn",
        ],
        "color": "#e67e22",
        "order": 2,
    },
    {
        "name": "行业垂直媒体",
        "relevance_level": 3,
        "domain_patterns": [
            "huxiu.com",
            "juejin.cn",
            "segmentfault.com",
            "csdn.net",
            "infoq.cn",
            "oschina.net",
            "sspai.com",
            "lieyunwang.com",
            "iyiou.com",
            "cyzone.cn",
            "woshipm.com",
        ],
        "color": "#2ecc71",
        "order": 3,
    },
    {
        "name": "社交平台",
        "relevance_level": 2,
        "domain_patterns": [
            "weibo.com",
            "weibo.cn",
            "douban.com",
            "bilibili.com",
            "xiaohongshu.com",
            "douyin.com",
            "tiktok.com",
            "mp.weixin.qq.com",
            "twitter.com",
            "x.com",
            "facebook.com",
            "instagram.com",
            "reddit.com",
        ],
        "color": "#3498db",
        "order": 4,
    },
    {
        "name": "个人博客/自媒体",
        "relevance_level": 1,
        "domain_patterns": [
            "jianshu.com",
            "cnblogs.com",
            "blog.csdn.net",
            "zhihu.com/people",
            "github.io",
            "wordpress.com",
            "medium.com",
            "substack.com",
            "notion.so",
            "toutiao.com",
            "baijiahao.baidu.com",
        ],
        "color": "#9b59b6",
        "order": 5,
    },
    {
        "name": "其他",
        "relevance_level": 0,
        "domain_patterns": [],
        "color": "#95a5a6",
        "order": 6,
    },
]


def ensure_default_categories():
    if LinkCategory.objects.exists():
        return
    for cat_data in DEFAULT_CATEGORIES:
        LinkCategory.objects.create(**cat_data)


def extractDomain(url):
    try:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def autoClassify(domain):
    if not domain:
        return _get_other_category()

    categories = LinkCategory.objects.exclude(name="其他").order_by("-relevance_level")
    for cat in categories:
        for pattern in cat.domain_patterns:
            if pattern in domain:
                return cat

    return _get_other_category()


_other_category_cache = None


def _get_other_category():
    global _other_category_cache
    if _other_category_cache is None:
        _other_category_cache = LinkCategory.objects.filter(name="其他").first()
    return _other_category_cache


def classifyLink(link_obj):
    if link_obj.category is not None:
        return link_obj.category

    domain = extractDomain(link_obj.link_url)
    category = autoClassify(domain)
    link_obj.category = category
    link_obj.is_manual = False
    link_obj.save(update_fields=["category", "is_manual"])
    return category


def classifyLinksBatch(link_objs):
    category_counts = {}
    for link in link_objs:
        cat = classifyLink(link)
        cat_name = cat.name if cat else "其他"
        category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
    return category_counts


def getCategoryStats(category_counts):
    ensure_default_categories()
    all_categories = LinkCategory.objects.all()
    result = {}
    for cat in all_categories:
        result[cat.name] = category_counts.get(cat.name, 0)
    return result


def getHighRelevanceRatio(category_counts):
    high_level_names = set(
        LinkCategory.objects.filter(relevance_level__gte=3).values_list(
            "name", flat=True
        )
    )
    high_count = sum(v for k, v in category_counts.items() if k in high_level_names)
    total = sum(category_counts.values())
    return round(high_count / total * 100, 2) if total > 0 else 0
