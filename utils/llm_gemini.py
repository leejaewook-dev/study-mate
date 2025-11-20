import os
import json
from typing import List, Dict, Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

# ────────────────────────────────────────────
# 0. 환경 변수에서 GEMINI_API_KEY 불러오기
# ────────────────────────────────────────────
load_dotenv(".env.study")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("환경변수 GEMINI_API_KEY가 설정되어 있지 않습니다. (.env.study 확인)")

client = genai.Client(api_key=GEMINI_API_KEY)


# ────────────────────────────────────────────
# 공통: 페이지 텍스트 정리
# ────────────────────────────────────────────
def _compress_pages(pages: List[str], limit: int = 8) -> List[str]:
    """
    앞쪽 limit개의 페이지만 사용하고, 각 페이지 텍스트 길이를 적당히 자른다.
    """
    out: List[str] = []
    for p in pages[:limit]:
        t = p.strip()
        if len(t) > 800:
            t = t[:800] + "\n...(생략)"
        out.append(t)
    return out


def _join_response_text(response) -> str:
    """
    Gemini response에서 텍스트 부분만 모아 하나의 문자열로 합친다.
    """
    parts: List[str] = []
    for c in response.candidates:
        if c.content and c.content.parts:
            for part in c.content.parts:
                if hasattr(part, "text") and part.text:
                    parts.append(part.text)
    return "\n".join(parts).strip()


# ────────────────────────────────────────────
# 1) 전체 강의 요약
# ────────────────────────────────────────────
def generate_whole_summary(pages: List[str]) -> str:
    pages_short = _compress_pages(pages, 8)
    context = "\n\n".join(f"[페이지 {i+1}]\n{t}" for i, t in enumerate(pages_short))

    prompt = f"""
너는 대학 강의 PPT를 분석하는 'Study-Mate' 학습 도우미다.

[입력 문맥]
{context}

[지시사항]
- 이 강의가 전반적으로 무엇을 다루는지 2~3문단, 총 6~10문장으로 작성해라.
- 핵심 주제, 목표, 전체 흐름 중심으로 설명해라.
- Markdown으로 작성.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
    except Exception as e:
        raise RuntimeError(f"Gemini 호출 오류(전체 요약): {repr(e)}")

    text = _join_response_text(response)
    return text or "전체 요약을 생성하지 못했습니다."


# ────────────────────────────────────────────
# 2) (옵션) 여러 페이지를 한 번에 대략 요약
#    - 지금 app.py에서 안 써도 되지만 import 되어 있으니 유지
# ────────────────────────────────────────────
def generate_page_summaries(pages: List[str]) -> str:
    pages_short = _compress_pages(pages, 8)
    context = "\n\n".join(f"[페이지 {i+1}]\n{t}" for i, t in enumerate(pages_short))

    prompt = f"""
너는 'Study-Mate'다. 아래 텍스트는 PPT 페이지 모음이다.

[입력 페이지들]
{context}

[지시사항]
- 각 페이지마다 '### 페이지 N 요약' 형식으로 요약해라.
- 개념 / 설명 / 절차 / 시험 포인트를 포함해라.
- Markdown으로 출력.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.25),
        )
    except Exception as e:
        raise RuntimeError(f"Gemini 호출 오류(페이지 요약): {repr(e)}")

    text = _join_response_text(response)
    return text or "페이지 요약을 생성하지 못했습니다."


# ────────────────────────────────────────────
# 3) 페이지별 문제 생성 (난이도 선택 + JSON 반환)
# ────────────────────────────────────────────
def generate_page_questions(pages: List[str], difficulty: str = "medium") -> List[Dict[str, Any]]:
    """
    반환: 각 문제를 나타내는 dict의 리스트

    [
      {
        "id": "P1Q1",
        "page": 1,
        "question": "문제 본문",
        "choices": {"1": "보기1", "2": "보기2", "3": "보기3", "4": "보기4"},
        "answer": 2,
        "explain": "해설"
      },
      ...
    ]
    """

    pages_short = _compress_pages(pages, 8)
    context = "\n\n".join(f"[페이지 {i+1}]\n{t}" for i, t in enumerate(pages_short))

    prompt = (
        "너는 대학 강의 PPT 기반 문제를 생성하는 'Study-Mate'다.\n\n"
        "[입력 페이지]\n"
        f"{context}\n\n"
        f"[난이도] {difficulty}\n\n"
        "[문제 생성 규칙]\n"
        "- 각 페이지마다 2문제씩 생성.\n"
        "- 각 문제는 4지선다 객관식.\n"
        "- 난이도 기준:\n"
        "  * easy: 기본 정의 중심, 직관적인 오답\n"
        "  * medium: 개념 비교·특징 구분\n"
        "  * hard: 응용, 간단한 계산이나 추론 포함\n\n"
        "[출력 형식]\n"
        "- 아무 설명 문장도 쓰지 말고, 오직 JSON 배열만 출력해라.\n"
        "- 각 원소는 아래 필드를 모두 포함해야 한다.\n"
        "{\n"
        "  \"id\": \"P1Q1\",                 // 문제 ID (페이지+번호)\n"
        "  \"page\": 1,                     // 몇 번째 페이지 기반인지\n"
        "  \"question\": \"문제 본문 문장\",\n"
        "  \"choices\": {\n"
        "    \"1\": \"보기1\",\n"
        "    \"2\": \"보기2\",\n"
        "    \"3\": \"보기3\",\n"
        "    \"4\": \"보기4\"\n"
        "  },\n"
        "  \"answer\": 2,                   // 정답 보기 번호 (정수)\n"
        "  \"explain\": \"왜 정답인지 한두 문장으로 설명\"\n"
        "}\n"
        "- JSON 이외의 텍스트는 절대 출력하지 마라."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.3),
        )
    except Exception as e:
        raise RuntimeError(f"Gemini 호출 오류(문제 생성): {repr(e)}")

    raw = _join_response_text(response)

    # 모델이 ```json ... ``` 형태로 감싸서 보낼 수도 있으니 껍데기 제거
    txt = raw.strip()
    if txt.startswith("```"):
        # ```json 또는 ``` 제거
        if txt.startswith("```json"):
            txt = txt[len("```json"):].strip()
        else:
            txt = txt[len("```"):].strip()
        # 끝에 ``` 있으면 제거
        if "```" in txt:
            txt = txt.split("```")[0].strip()

    try:
        questions = json.loads(txt)
    except Exception:
        print("JSON 파싱 실패, raw 응답:", raw)
        questions = []

    # 리스트가 아닐 경우 대비
    if not isinstance(questions, list):
        questions = []

    return questions


# ────────────────────────────────────────────
# 4) 단일 페이지 상세 요약 (이미지 옆에 붙일용)
# ────────────────────────────────────────────
def generate_single_page_summary(page_text: str, page_number: int) -> str:
    """
    특정 페이지 한 장을 공부용으로 자세히 요약하는 함수
    """

    prompt = f"""
너는 대학 강의 PPT를 공부용으로 정리하는 전문 튜터 'Study-Mate'다.

[페이지 {page_number} 내용]
{page_text}

[요약 지침]
- 학생이 이 페이지만 보고도 완벽히 이해할 수 있도록 친절하고 깊이 있게 설명해라.
- 불필요한 잡설은 하지 말고, 개념/절차/시험포인트 중심으로 정리해라.
- 계산 예시나 알고리즘이 있다면 핵심 단계만 단계별로 정리해라.

[출력 형식]

### 📘 페이지 {page_number} 요약

- **[개념]** 이 페이지의 핵심 개념을 1~2문장으로 요약
- **[설명]** 슬라이드 그림/표/텍스트가 설명하는 내용을 2~4문장으로 서술
- **[예시/절차]** 해당 페이지의 계산/알고리즘 예시가 있다면 핵심 단계 요약
- **[시험 포인트]** 시험에서 반드시 기억해야 할 포인트 1~2줄
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.25),
        )
    except Exception as e:
        raise RuntimeError(f"Gemini 호출 오류(단일 페이지 요약): {repr(e)}")

    text = _join_response_text(response)
    return text or f"페이지 {page_number} 요약을 생성하지 못했습니다."
