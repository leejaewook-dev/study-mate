# utils/extract_pdf.py

from pathlib import Path
import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path: str | Path) -> list[str]:
    """
    주어진 PDF 파일 경로에서 페이지별 텍스트를 추출하여 리스트로 반환.
    각 요소는 한 페이지(슬라이드)에 해당하는 문자열.
    """
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)

    pages: list[str] = []
    for page in doc:
        # 기본 텍스트 추출
        text = page.get_text("text") or ""
        text = text.strip()

        # 완전히 비어 있는 페이지는 스킵 (원하면 유지해도 됨)
        if text:
            pages.append(text)
        else:
            pages.append("")  # 페이지 수를 맞추고 싶으면 이렇게 남겨도 됨

    doc.close()
    return pages
