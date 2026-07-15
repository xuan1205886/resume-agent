"""
向量检索器 — 复用 rag-qa-system 的 Chroma query 模式
使用共享 Embedding 模型避免重复加载
"""

from typing import List, Optional

from sentence_transformers import SentenceTransformer

from src.indexing.indexer import get_index_builder
from src.indexing.embedding_model import get_embedding_model
from src.config import get_config


class Retriever:
    """向量检索器"""

    def __init__(self):
        config = get_config()
        self.top_k = config.retrieval.top_k
        self.similarity_threshold = config.retrieval.similarity_threshold
        self._builder = None

    @property
    def builder(self):
        if self._builder is None:
            self._builder = get_index_builder()
        return self._builder

    @property
    def model(self) -> SentenceTransformer:
        """使用全局共享的 Embedding 模型，避免重复加载"""
        return get_embedding_model()

    def query(
        self,
        collection_name: str,
        query_text: str,
        top_k: Optional[int] = None,
    ) -> List[dict]:
        """查询指定 collection

        Args:
            collection_name: collection 名称
            query_text: 查询文本
            top_k: 返回数量（默认使用配置值）

        Returns:
            [{"id": ..., "content": ..., "metadata": ..., "score": ...}, ...]
        """
        if top_k is None:
            top_k = self.top_k

        collection = self.builder.client.get_collection(collection_name)

        query_embedding = self.model.encode(
            [query_text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        docs = []
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            score = 1.0 - distance  # 余弦距离转相似度

            if score < self.similarity_threshold:
                continue

            docs.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "score": round(score, 4),
            })

        return docs

    def multi_query(
        self,
        collection_names: List[str],
        query_text: str,
        top_k: Optional[int] = None,
    ) -> dict[str, List[dict]]:
        """查询多个 collection

        Returns:
            {collection_name: [docs], ...}
        """
        results = {}
        for name in collection_names:
            try:
                results[name] = self.query(name, query_text, top_k)
            except Exception:
                results[name] = []
        return results


_retriever: Optional[Retriever] = None


def get_retriever() -> Retriever:
    """获取检索器单例"""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever
