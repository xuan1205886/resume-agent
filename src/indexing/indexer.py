"""
Chroma 向量索引构建器 — 复用 rag-qa-system 的 PersistentClient 模式
支持批量嵌入和增量索引，使用共享 Embedding 模型
"""

import os
from typing import List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.config import get_config
from src.indexing.embedding_model import get_embedding_model


class IndexBuilder:
    """Chroma 索引构建器"""

    def __init__(self):
        config = get_config()
        self.persist_dir = os.path.abspath(config.knowledge_base.persist_dir)
        self.batch_size = config.embedding.batch_size

        self._client = None

    @property
    def client(self) -> chromadb.PersistentClient:
        """懒加载 Chroma 客户端"""
        if self._client is None:
            os.makedirs(self.persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def model(self) -> SentenceTransformer:
        """使用全局共享的 Embedding 模型，避免重复加载"""
        return get_embedding_model()

    def create_collection(self, collection_name: str) -> chromadb.Collection:
        """创建或获取 collection（余弦空间）"""
        try:
            collection = self.client.get_collection(collection_name)
        except Exception:
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return collection

    def index_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[dict],
        ids: Optional[List[str]] = None,
    ) -> int:
        """将文档批量索引入 Chroma

        Args:
            collection_name: collection 名称
            documents: 文档文本列表
            metadatas: 每个文档的元数据
            ids: 文档ID列表（可选，默认自动生成）

        Returns:
            索引的文档数量
        """
        collection = self.create_collection(collection_name)

        if ids is None:
            ids = [f"{collection_name}_{i:05d}" for i in range(len(documents))]

        total = 0
        for i in tqdm(range(0, len(documents), self.batch_size), desc=f"索引 {collection_name}"):
            batch_docs = documents[i:i + self.batch_size]
            batch_ids = ids[i:i + self.batch_size]
            batch_meta = metadatas[i:i + self.batch_size]

            embeddings = self.model.encode(
                batch_docs,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

            collection.add(
                ids=batch_ids,
                embeddings=embeddings.tolist(),
                documents=batch_docs,
                metadatas=batch_meta,
            )
            total += len(batch_docs)

        return total

    def clear_collection(self, collection_name: str):
        """清除指定 collection"""
        try:
            self.client.delete_collection(collection_name)
        except Exception:
            pass


# 模块级单例
_index_builder: Optional[IndexBuilder] = None


def get_index_builder() -> IndexBuilder:
    """获取索引构建器单例"""
    global _index_builder
    if _index_builder is None:
        _index_builder = IndexBuilder()
    return _index_builder
