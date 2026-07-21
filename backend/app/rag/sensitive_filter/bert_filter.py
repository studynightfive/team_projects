"""Layer 2: 基于 BERT 的语义理解和意图识别过滤

使用 bert-base-chinese 模型进行语义编码，通过对比问题与
敏感/正常锚点短语的语义相似度来判断问题意图是否敏感。

模型在首次使用时延迟加载（lazy loading），加载后缓存在内存中。
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

import numpy as np
import numpy.typing as npt

MODULE_LOGGER = logging.getLogger(__name__)


class BertSensitiveFilter:
    """BERT 语义敏感内容过滤器

    使用预训练的中文 BERT 模型对问题进行语义编码，
    通过计算与敏感锚点和正常锚点的余弦相似度来判断意图。

    模型在首次调用时自动下载并加载到内存（约 400MB），
    后续请求直接使用缓存的模型，无需重复加载。
    """

    MODEL_NAME: ClassVar[str] = "bert-base-chinese"

    # 敏感意图语义锚点 — 定义各类敏感提问的语义方向
    SENSITIVE_ANCHORS: ClassVar[list[str]] = [
        "如何攻击系统漏洞获取权限",
        "制作违法危险物品的方法",
        "色情淫秽暴力血腥内容",
        "窃取盗取他人隐私信息",
        "破坏删除计算机系统数据",
        "诈骗欺骗非法获取钱财",
        "绕过安全防护机制入侵",
        "泄露传播国家机密信息",
        "煽动颠覆对抗政府统治",
        "恶意散播病毒木马程序",
    ]

    # 正常提问语义锚点 — 定义各类正常工作查询的语义方向
    NORMAL_ANCHORS: ClassVar[list[str]] = [
        "如何提高团队的工作效率",
        "公司最新的考勤管理制度",
        "差旅费用报销的标准流程",
        "产品的功能特性和使用方法",
        "技术文档使用说明和示例",
        "项目进度报告和关键节点",
        "客户服务支持的标准流程",
        "数据分析方法论和工具推荐",
        "企业知识库中的政策规定",
        "员工培训和职业发展路径",
    ]

    def __init__(self, threshold: float = 0.62) -> None:
        """初始化 BERT 过滤器

        Args:
            threshold: 相似度阈值。当问题与敏感锚点的余弦相似度
                       超过此值且高于正常锚点相似度时，判定为敏感。
                       默认 0.62 经过调优，兼顾准确率和召回率。
        """
        self._threshold = threshold
        self._model: Any = None  # transformers AutoModel
        self._tokenizer: Any = None  # transformers AutoTokenizer
        self._sensitive_embeddings: npt.NDArray[np.float32] | None = None
        self._normal_embeddings: npt.NDArray[np.float32] | None = None

    def _lazy_load(self) -> None:
        """延迟加载 BERT 模型和预计算锚点嵌入"""
        if self._model is not None:
            return

        MODULE_LOGGER.info("加载 BERT 模型用于敏感词过滤: %s", self.MODEL_NAME)
        try:
            from transformers import AutoModel, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self._model = AutoModel.from_pretrained(self.MODEL_NAME)
            self._model.eval()

            # 预计算所有锚点嵌入
            all_anchors = self.SENSITIVE_ANCHORS + self.NORMAL_ANCHORS
            embeddings = self._encode_batch(all_anchors)
            n_sensitive = len(self.SENSITIVE_ANCHORS)
            self._sensitive_embeddings = embeddings[:n_sensitive]
            self._normal_embeddings = embeddings[n_sensitive:]

            MODULE_LOGGER.info("BERT 模型加载完成，锚点嵌入已预计算")
        except ImportError:
            MODULE_LOGGER.warning(
                "transformers/torch 未安装，BERT 过滤器不可用。"
                "请安装: pip install transformers torch"
            )
            raise
        except Exception as exc:
            MODULE_LOGGER.error("BERT 模型加载失败: %s", exc)
            raise

    def _encode_batch(self, texts: list[str]) -> npt.NDArray[np.float32]:
        """批量编码文本为句子嵌入（mean pooling）

        使用 mean pooling 将所有 token 的输出取平均作为句子级嵌入。
        """
        import torch

        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="pt",
        )
        with torch.no_grad():
            outputs = self._model(**encoded)

        # Mean pooling
        attention_mask = encoded["attention_mask"]
        token_embeddings = outputs.last_hidden_state
        mask_expanded = (
            attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        )
        sum_embeddings = torch.sum(token_embeddings * mask_expanded, 1)
        sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
        mean_embeddings = sum_embeddings / sum_mask

        return mean_embeddings.numpy()

    @staticmethod
    def _cosine_similarity(
        a: npt.NDArray[np.float32], b: npt.NDArray[np.float32]
    ) -> float:
        """计算两个向量的余弦相似度"""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def check(self, text: str) -> tuple[bool, float, str]:
        """使用 BERT 语义理解检查问题意图

        Args:
            text: 用户输入的问题文本

        Returns:
            tuple:
                - is_sensitive (bool): 是否判定为敏感
                - confidence (float): 置信度分数 (0.0-1.0)
                - matched_label (str): 最匹配的敏感意图描述
        """
        self._lazy_load()
        assert self._sensitive_embeddings is not None
        assert self._normal_embeddings is not None
        sensitive_emb = self._sensitive_embeddings
        normal_emb = self._normal_embeddings

        # 编码问题
        question_emb = self._encode_batch([text])[0]

        # 计算与敏感锚点和正常锚点质心的相似度
        sensitive_centroid = sensitive_emb.mean(axis=0)
        normal_centroid = normal_emb.mean(axis=0)

        sensitive_sim = self._cosine_similarity(question_emb, sensitive_centroid)
        normal_sim = self._cosine_similarity(question_emb, normal_centroid)

        # 找到最匹配的单个敏感锚点作为说明
        best_idx = max(
            range(len(self.SENSITIVE_ANCHORS)),
            key=lambda i: self._cosine_similarity(
                question_emb, sensitive_emb[i]
            ),
        )
        matched_label = f"敏感意图: {self.SENSITIVE_ANCHORS[best_idx]}"

        # 分类逻辑
        is_sensitive = (
            sensitive_sim > self._threshold and sensitive_sim > normal_sim
        )

        confidence = float(sensitive_sim)

        MODULE_LOGGER.debug(
            "BERT敏感检查: text_len=%d sensitive_sim=%.4f normal_sim=%.4f "
            "threshold=%.2f is_sensitive=%s",
            len(text),
            sensitive_sim,
            normal_sim,
            self._threshold,
            is_sensitive,
        )

        return is_sensitive, confidence, matched_label


# 全局单例，避免重复加载模型
_bert_filter_instance: BertSensitiveFilter | None = None


def get_bert_filter() -> BertSensitiveFilter:
    """获取 BERT 过滤器全局单例"""
    global _bert_filter_instance
    if _bert_filter_instance is None:
        _bert_filter_instance = BertSensitiveFilter()
    return _bert_filter_instance


def check_bert(text: str) -> tuple[bool, float, str]:
    """Layer 2 入口：BERT 语义敏感检查

    便捷函数，可直接从 service 层调用。

    Returns:
        tuple: (是否敏感, 置信度, 匹配标签)
    """
    try:
        bert = get_bert_filter()
        return bert.check(text)
    except (ImportError, Exception) as exc:
        # BERT 不可用时降级：仅依赖 Layer 1
        MODULE_LOGGER.warning("BERT 过滤器不可用，跳过 Layer 2 检查: %s", exc)
        return False, 0.0, f"BERT不可用({type(exc).__name__})"
