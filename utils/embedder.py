# utils/embedder.py

from typing import List
from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

def get_model() -> SentenceTransformer:
    """SentenceTransformer 모델을 lazy load."""
    global _model
    if _model is None:
        # 가벼우면서도 성능 괜찮은 기본 모델
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    여러 개의 텍스트를 임베딩하여 2차원 리스트(embeddings)로 반환.
    """
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings.tolist()
