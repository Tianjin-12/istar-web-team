"""
聚类可视化数据处理工具类
用于加载、处理和转换聚类相关数据
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

# 添加 Django 项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

import django

from mvp.models import ZhihuQuestion, QuestionBank


class ClusterDataProcessor:
    """聚类数据处理器

    职责：
    - 加载本地 npy/json 文件
    - 加载数据库中的问题文本和关注点
    - 降维处理（UMAP/PCA/t-SNE）
    - 计算聚类统计指标
    - 生成 k-distance 曲线数据
    """

    def __init__(self, keyword):
        """
        初始化数据处理器

        Args:
            keyword: 关键词，用于筛选数据
        """
        self.keyword = keyword

        # 获取项目根目录
        self.project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        # 加载数据
        self.embeddings = self._load_embeddings()
        self.cluster_map = self._load_cluster_map()
        self.questions = self._load_questions()
        self.intents = self._load_intents()

        # 验证数据一致性
        self._validate_data()

    def _load_embeddings(self):
        """加载向量文件"""
        try:
            embedding_path = os.path.join(self.project_root, "question_embeddings.npy")
            embeddings = np.load(embedding_path)
            print(f"[ClusterDataProcessor] 加载向量文件成功: {embeddings.shape}")
            return embeddings
        except FileNotFoundError:
            raise FileNotFoundError(f"未找到向量文件: {embedding_path}")

    def _load_cluster_map(self):
        """加载聚类映射文件"""
        try:
            cluster_map_path = os.path.join(self.project_root, "final_cluster_map.json")
            with open(cluster_map_path, "r", encoding="utf-8") as f:
                cluster_map = json.load(f)
            print(f"[ClusterDataProcessor] 加载聚类映射成功: {len(cluster_map)} 个问题")
            return cluster_map
        except FileNotFoundError:
            raise FileNotFoundError(f"未找到聚类映射文件: {cluster_map_path}")

    def _load_questions(self):
        """从数据库加载问题文本"""
        questions = list(
            ZhihuQuestion.objects.filter(keyword=self.keyword)
            .order_by("question_id")
            .values_list("question_text", flat=True)
        )

        # 构建索引到问题文本的映射（索引从0开始）
        question_map = {i: q for i, q in enumerate(questions)}
        print(f"[ClusterDataProcessor] 加载问题文本成功: {len(question_map)} 个问题")
        return question_map

    def _load_intents(self):
        """从数据库加载聚类关注点"""
        # 按簇ID分组获取关注点
        cluster_data = {}

        records = (
            QuestionBank.objects.filter(keyword=self.keyword)
            .values("cluster_id", "main_intent")
            .distinct()
        )

        for record in records:
            cluster_id = record["cluster_id"]
            intent = record["main_intent"]

            # 解析 JSON 格式的关注点
            if isinstance(intent, str):
                try:
                    intent_obj = json.loads(intent)
                    # 提取主要关键词
                    keywords = intent_obj.get("主要关键词", [])
                    cluster_data[cluster_id] = (
                        ", ".join(keywords) if keywords else intent[:100]
                    )
                except json.JSONDecodeError:
                    cluster_data[cluster_id] = intent[:100]
            else:
                cluster_data[cluster_id] = str(intent)[:100]

        print(f"[ClusterDataProcessor] 加载关注点成功: {len(cluster_data)} 个簇")
        return cluster_data

    def _validate_data(self):
        """验证数据一致性"""
        if len(self.embeddings) != len(self.questions):
            print(
                f"[ClusterDataProcessor] 警告: 向量数量({len(self.embeddings)}) != 问题数量({len(self.questions)})"
            )

        if len(self.cluster_map) != len(self.questions):
            print(
                f"[ClusterDataProcessor] 警告: 聚类映射数量({len(self.cluster_map)}) != 问题数量({len(self.questions)})"
            )

    def reduce_dimension(self, method="umap", n_components=3):
        """
        降维处理

        Args:
            method: 降维方法 ('umap', 'pca', 'tsne')
            n_components: 降维后的维度 (2 或 3)

        Returns:
            降维后的向量数组
        """
        try:
            if method == "umap":
                import umap

                reducer = umap.UMAP(
                    n_components=n_components,
                    random_state=42,
                    n_neighbors=15,
                    min_dist=0.1,
                )
                reduced = reducer.fit_transform(self.embeddings)
                print(
                    f"[ClusterDataProcessor] UMAP 降维完成: {method.upper()}, {n_components}D"
                )
            elif method == "pca":
                reducer = PCA(n_components=n_components, random_state=42)
                reduced = reducer.fit_transform(self.embeddings)
                print(
                    f"[ClusterDataProcessor] PCA 降维完成: {method.upper()}, {n_components}D"
                )
            elif method == "tsne":
                reducer = TSNE(
                    n_components=n_components, random_state=42, perplexity=30
                )
                reduced = reducer.fit_transform(self.embeddings)
                print(
                    f"[ClusterDataProcessor] t-SNE 降维完成: {method.upper()}, {n_components}D"
                )
            else:
                raise ValueError(f"不支持的降维方法: {method}")

            return reduced
        except ImportError as e:
            print(f"[ClusterDataProcessor] UMAP 未安装，切换到 PCA")
            reducer = PCA(n_components=n_components, random_state=42)
            return reducer.fit_transform(self.embeddings)

    def get_cluster_stats(self):
        """
        获取聚类统计信息

        Returns:
            包含聚类统计的字典
        """
        total = len(self.embeddings)
        noise = sum(1 for cid in self.cluster_map.values() if cid == -1)
        valid = total - noise

        clusters = {}
        for qid, cid in self.cluster_map.items():
            if cid >= 0:
                clusters[cid] = clusters.get(cid, 0) + 1

        stats = {
            "total": total,
            "noise": noise,
            "noise_percent": round(noise / total * 100, 1) if total > 0 else 0,
            "valid_clusters": valid,
            "valid_percent": round(valid / total * 100, 1) if total > 0 else 0,
            "cluster_count": len(clusters),
            "clusters": {},
        }

        # 添加每个簇的统计
        for cluster_id, count in sorted(clusters.items()):
            stats["clusters"][cluster_id] = {
                "count": count,
                "percent": round(count / valid * 100, 1) if valid > 0 else 0,
            }

        print(
            f"[ClusterDataProcessor] 聚类统计: 总数={total}, 噪声={noise}, 簇数={len(clusters)}"
        )
        return stats

    def get_k_distance_data(self, k=4):
        """
        计算 k-distance 曲线数据

        Args:
            k: 近邻数

        Returns:
            排序后的 k-distance 数组
        """
        nn = NearestNeighbors(n_neighbors=k).fit(self.embeddings)
        distances = nn.kneighbors(self.embeddings)[0][:, -1]
        sorted_distances = np.sort(distances)

        print(f"[ClusterDataProcessor] k-distance 计算完成: k={k}")
        return sorted_distances

    def get_cluster_details(self, cluster_id):
        """
        获取指定簇的详细信息

        Args:
            cluster_id: 簇 ID

        Returns:
            包含簇详细信息的字典
        """
        # 获取该簇的所有问题ID
        question_ids = [
            int(qid) for qid, cid in self.cluster_map.items() if cid == cluster_id
        ]

        # 获取问题文本
        question_texts = []
        for qid in sorted(question_ids):
            # cluster_map 中的 ID 是从 1 开始的，需要转换为从 0 开始的索引
            idx = qid - 1
            if idx in self.questions:
                question_texts.append(self.questions[idx])

        # 获取关注点
        intent = self.intents.get(cluster_id, "无关注点描述")

        details = {
            "cluster_id": cluster_id,
            "question_count": len(question_ids),
            "question_ids": sorted(question_ids),
            "intent": intent,
            "questions": question_texts,
        }

        print(
            f"[ClusterDataProcessor] 获取簇详情: 簇 {cluster_id}, 问题数={len(question_ids)}"
        )
        return details

    def get_available_keywords(self):
        """
        获取所有可用的关键词

        Returns:
            关键词列表
        """
        keywords = list(
            ZhihuQuestion.objects.values_list("keyword", flat=True).distinct()
        )
        print(f"[ClusterDataProcessor] 可用关键词: {len(keywords)} 个")
        return keywords

    def calculate_silhouette_score(self):
        """
        计算轮廓系数

        Returns:
            轮廓系数（-1 到 1，越接近 1 越好）
        """
        # 获取所有有效样本的标签（排除噪声点）
        valid_indices = []
        labels = []

        for qid, cid in self.cluster_map.items():
            if cid != -1:
                idx = int(qid) - 1  # 转换为从 0 开始的索引
                valid_indices.append(idx)
                labels.append(cid)

        if len(valid_indices) < 2:
            return 0.0

        valid_embeddings = self.embeddings[valid_indices]

        try:
            score = silhouette_score(valid_embeddings, labels)
            print(f"[ClusterDataProcessor] 轮廓系数: {score:.4f}")
            return round(score, 4)
        except Exception as e:
            print(f"[ClusterDataProcessor] 计算轮廓系数失败: {e}")
            return 0.0
