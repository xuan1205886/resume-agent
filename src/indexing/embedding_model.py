"""
共享 Embedding 模型 — 全局单例，避免 Retriever 和 IndexBuilder 重复加载
SentenceTransformer 模型约 470MB，共享可节省约 500MB 内存
"""

import logging
from typing import Optional

from sentence_transformers import SentenceTransformer

from src.config import get_config

logger = logging.getLogger("embedding_model")

_embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """获取全局共享的 Embedding 模型实例

    首次调用时加载模型，后续调用返回同一实例。
    避免 Retriever 和 IndexBuilder 各自加载一份模型。

    Returns:
        SentenceTransformer 模型实例
    """
    global _embedding_model
    if _embedding_model is None:
        config = get_config()
        logger.info(f"加载 Embedding 模型: {config.embedding.model_name} (device={config.embedding.device})")
        _embedding_model = SentenceTransformer(
            config.embedding.model_name,
            device=config.embedding.device,
        )
        logger.info("Embedding 模型加载完成")
    return _embedding_model


def reset_embedding_model():
    """重置 Embedding 模型（测试用）"""
    global _embedding_model
    _embedding_model = None
