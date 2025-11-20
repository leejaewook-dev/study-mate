# utils/chunker.py

from typing import List

def chunk_text(
    text: str,
    chunk_size: int = 300,
    overlap: int = 100
) -> List[str]:
    """
    텍스트를 일정 길이(chunk_size)만큼 자르고,
    overlap 길이만큼 겹치도록 분할하는 함수.
    """
    words = text.split()
    chunks: List[str] = []

    start = 0
    n = len(words)

    while start < n:
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk = " ".join(chunk_words).strip()

        if chunk:
            chunks.append(chunk)

        start += (chunk_size - overlap)  # 오버랩 적용

    return chunks


def split_pages_to_chunks(
    pages: List[str],
    chunk_size: int = 300,
    overlap: int = 100
) -> List[str]:
    """
    여러 페이지(pages 리스트)를 받아
    페이지별로 chunk_text를 적용한 뒤 전체를 하나로 합쳐 반환.
    """
    all_chunks = []

    for page in pages:
        page = page.strip()
        if not page:
            continue

        chunks = chunk_text(page, chunk_size, overlap)
        all_chunks.extend(chunks)

    return all_chunks
