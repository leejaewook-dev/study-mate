# utils/chroma_db.py

from typing import List, Dict
from pathlib import Path
import uuid

import chromadb
from chromadb.config import Settings

from utils.embedder import embed_texts

# Chroma Persistent DB 설정 (폴더에 저장)
CHROMA_DIR = Path("chroma_db")
CHROMA_DIR.mkdir(exist_ok=True)

_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

_COLLECTION_NAME = "study_mate"
_collection = _client.get_or_create_collection(
    name=_COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}  # 코사인 유사도
)


def add_chunks(chunks: List[str], source_name: str) -> None:
    """
    청크 리스트를 임베딩하고, Chroma 컬렉션에 저장.
    source_name: 업로드한 파일 이름 등.
    """
    if not chunks:
        return

    embeddings = embed_texts(chunks)

    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"source": source_name, "index": i} for i in range(len(chunks))]

    _collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )


def query_similar(query: str, top_k: int = 5) -> Dict:
    """
    질의문(query)을 임베딩하여, 상위 top_k 유사 문단을 검색.
    """
    query_emb = embed_texts([query])[0]  # 하나만 넣었으니 [0] 사용

    result = _collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
    )
    return result
