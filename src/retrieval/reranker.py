"""
BGE Reranker 重排序器 — 复用 rag-qa-system 的 Cross-Encoder 模式
"""

from typing import List, Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.config import get_config


class Reranker:
    """BGE Cross-Encoder Reranker"""

    def __init__(self):
        config = get_config()
        self.model_name = config.reranker.model_name
        self.batch_size = config.reranker.batch_size
        self.device = config.reranker.device

        self._tokenizer = None
        self._model = None

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        return self._tokenizer

    @property
    def model(self):
        if self._model is None:
            self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self._model.to(self.device)
            self._model.eval()
        return self._model

    def rerank(
        self,
        query: str,
        documents: List[str],
        batch_size: Optional[int] = None,
    ) -> List[float]:
        """对文档进行重排序评分

        Args:
            query: 查询文本
            documents: 文档文本列表
            batch_size: 批处理大小

        Returns:
            每个文档的相关性分数列表 (0-1)
        """
        if not documents:
            return []
        if batch_size is None:
            batch_size = self.batch_size

        all_scores = []
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            scores = self._score_batch(query, batch_docs)
            all_scores.extend(scores)

        return all_scores

    def _score_batch(self, query: str, documents: List[str]) -> List[float]:
        """对一批文档打分"""
        inputs = self.tokenizer(
            [query] * len(documents),
            documents,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            scores = outputs.logits[:, 0].cpu().tolist()

        return [round(max(0.0, min(1.0, s)), 4) for s in scores]

    def rerank_results(
        self,
        query: str,
        results: List[dict],
    ) -> List[dict]:
        """对已有检索结果进行重排序

        Args:
            query: 查询文本
            results: 检索结果列表 [{"content": ..., "score": ...}, ...]

        Returns:
            按 reranker 分数降序排列的结果
        """
        if not results:
            return results

        contents = [r.get("content", "") for r in results]
        scores = self.rerank(query, contents)

        for i, score in enumerate(scores):
            results[i]["rerank_score"] = score

        results.sort(key=lambda r: r.get("rerank_score", 0), reverse=True)
        return results


_reranker: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """获取 Reranker 单例"""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
