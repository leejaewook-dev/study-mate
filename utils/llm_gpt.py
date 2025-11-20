# utils/llm_gpt.py

from typing import List
import os

# ---------------------------------------------------
# 0) .env.study 로부터 OPENAI_API_KEY 로드
# ---------------------------------------------------
# python-dotenv가 없더라도 import 에러로 죽지 않게 try/except 처리
try:
    from dotenv import load_dotenv
    # app.py가 있는 루트에서 실행된다고 가정하고, 같은 위치의 .env.study 로드
    load_dotenv(".env.study")
except ImportError:
    # dotenv 미설치여도 그냥 넘어가고, 나중에 os.getenv로만 시도
    pass

# OpenAI SDK (>= 1.40.0 기준)
try:
    from openai import OpenAI
except ImportError as e:
    # 이 상태면 import 단계에서 바로 죽으니까,
    # 에러 메시지를 보고 싶으면 print 해도 되지만 여기서는 조용히 두고,
    # 실제 호출 시에 설명해주는 쪽으로 처리할 수도 있음.
    OpenAI = None  # type: ignore

# 사용할 기본 모델 이름
MODEL_NAME = "gpt-4o-mini"


def get_gpt_client():
    """
    OpenAI GPT 클라이언트 생성.
    환경변수 OPENAI_API_KEY 에서 키를 읽어온다.
    """
    if OpenAI is None:
        # openai 패키지 자체가 없는 경우
        raise RuntimeError(
            "openai 패키지를 찾을 수 없습니다. "
            "가상환경에서 `pip install 'openai>=1.40.0'` 을 실행해 주세요."
        )

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "환경변수 OPENAI_API_KEY가 설정되어 있지 않습니다.\n"
            ".env.study 파일 또는 시스템 환경변수에 OPENAI_API_KEY=... 를 설정해 주세요."
        )
    return OpenAI(api_key=api_key)


def _call_gpt(prompt: str, model: str = MODEL_NAME) -> str:
    """
    공통 GPT 호출 유틸.
    - 응답 텍스트를 그대로 반환
    - 호출 중 에러가 나면 RuntimeError를 던지지 않고 에러 내용을 문자열로 반환
      (Streamlit 앱이 죽지 않도록 하기 위함)
    """
    try:
        client = get_gpt_client()
    except RuntimeError as e:
        # 클라이언트 생성 단계에서부터 문제가 있으면, 여기서 문자열로 반환
        return f"❌ GPT 클라이언트 생성 중 오류가 발생했습니다.\n\n에러 내용: `{e}`"

    try:
        response = client.responses.create(
            model=model,
            input=prompt,
        )
        return response.output_text or "❌ GPT 응답이 비어 있습니다."
    except Exception as e:
        # 여기서는 예외를 던지지 않고, 에러 내용을 문자열로 돌려줌
        return f"❌ GPT 호출 중 오류가 발생했습니다.\n\n에러 내용: `{e}`"


# ─────────────────────────────
# 공통: 문맥 합치기 (Q&A용)
# ─────────────────────────────
def build_context_from_docs(docs: List[str]) -> str:
    return "\n\n---\n\n".join(docs)


# ─────────────────────────────
# 1) 강의 전체 상세 요약 (Q&A용)
# ─────────────────────────────
def generate_detailed_summary(docs: List[str]) -> str:
    context = build_context_from_docs(docs)

    prompt = f"""
    너는 대학 강의 PPT를 정리해주는 한국어 학습 도우미 'Study-Mate'다.

    [강의 문맥]
    {context}

    [역할]
    - 아래 문맥에 있는 내용만 사용해서 대답해라.
    - 문맥에 없는 내용을 상상으로 만들지 마라.
    - '감사합니다', '경청해주셔서' 같은 인사 슬라이드는 무시해라.
    - 한국어로 대답해라.

    [요구사항 - 상세 요약]
    아래 형식으로, 비교적 자세하게 강의를 정리해라. Markdown으로 작성해라.

    ## 1. 강의 상세 요약

    - 이 강의(또는 해당 범위)의 흐름을 2~3개 단락으로 나누어 서술식으로 정리해라.
    - 전체 분량은 최소 8문장 이상, 15문장 이하로 작성해라.
    - 가능한 경우, 다음 구조를 따르도록 노력해라:
      1) 도입: 이 강의에서 다루는 주제와 배경
      2) 전개: 핵심 개념/정의/수식/알고리즘의 설명
      3) 마무리: 이 내용이 왜 중요한지, 어디에 응용되는지
    """

    return _call_gpt(prompt)


# ─────────────────────────────
# 2) 연습문제 생성 (Q&A용)
# ─────────────────────────────
def generate_questions_from_docs(docs: List[str]) -> str:
    context = build_context_from_docs(docs)

    prompt = f"""
    너는 대학 강의 PPT를 바탕으로 연습문제를 만들어주는 'Study-Mate'다.

    [강의 문맥]
    {context}

    [역할]
    - 아래 문맥에 있는 내용만 사용해서 문제를 만들어라.
    - 문맥에 없는 내용을 상상으로 만들지 마라.
    - '감사합니다', '경청해주셔서' 같은 인사 슬라이드는 무시해라.
    - 한국어로 대답해라.

    [요구사항 - 문제 생성]
    아래 형식으로 연습문제를 만들어라. Markdown으로 작성해라.

    ## 2. 객관식 연습문제 (2문제, 4지선다)
    - 실제 문맥에 등장한 용어나 개념을 기반으로 문제를 만들어라.
    - 개념의 정의, 특징, 비교 등을 묻는 문제로 구성해라.
    - 각 문제 아래에 정답 번호를 명시해라.

    ### Q1.
    (문제)

    1) (보기1)
    2) (보기2)
    3) (보기3)
    4) (보기4)

    정답: 2번

    ### Q2.
    (문제)

    1) (보기1)
    2) (보기2)
    3) (보기3)
    4) (보기4)

    정답: X번

    ## 3. 주관식 연습문제 (1~2문제)
    - 핵심 개념의 정의, 차이점, 장단점을 묻는 문제로 만들어라.
    - 각 문제 아래에 "정답 핵심 키워드"를 한 줄로 적어라.

    ### 서술형 Q1.
    (문제)

    정답 핵심 키워드: ...
    """

    return _call_gpt(prompt)


# ─────────────────────────────
# 3) Q&A용: 요약 + 문제 한 번에
# ─────────────────────────────
def generate_summary_and_questions(docs: List[str], user_query: str) -> str:
    """
    추가 질문 탭에서:
    - 관련 문단(docs)을 요약 + 문제 세트로 만들어서
      답변처럼 보여줄 때 사용하는 함수
    """
    summary_md = generate_detailed_summary(docs)
    questions_md = generate_questions_from_docs(docs)
    return summary_md.rstrip() + "\n\n---\n\n" + questions_md.lstrip()


# ─────────────────────────────
# 4) PPT 전체 → 1) 2줄 요약
#                 2) 페이지별 상세 요약(최대 8p)
#                 3) 페이지별 2문제씩 연습문제
# ─────────────────────────────
def generate_study_pack_from_pages(pages: List[str]) -> str:
    """
    전체 PPT에 대해:
    1) 전체 내용을 2줄로 요약
    2) 페이지별 학습용 상세 요약 (최대 8페이지)
    3) 각 페이지당 연습문제 2개씩 (최대 8페이지에 대해)

    를 한 번에 생성해서 Markdown으로 반환하는 함수.
    """

    # 페이지 수 & 길이 제한
    max_pages = min(len(pages), 8)       # 최대 8페이지 사용
    max_chars_per_page = 800             # 페이지당 최대 800자 사용

    context_blocks = []
    for i, page_text in enumerate(pages[:max_pages], start=1):
        text = page_text.strip()
        if len(text) > max_chars_per_page:
            text = text[:max_chars_per_page] + "\n...(이하 생략)"
        context_blocks.append(f"[페이지 {i}]\n{text}")

    context = "\n\n".join(context_blocks)

    prompt = f"""
    너는 대학 강의 PPT를 정리해주는 한국어 학습 도우미 'Study-Mate'다.

    아래는 PDF로 변환된 강의자료의 페이지별 텍스트이다.
    각 [페이지 N] 블록은 PPT의 한 슬라이드라고 생각하면 된다.
    페이지는 최대 8개까지만 주어진다.

    [강의 전체 문맥]
    {context}

    [역할]
    - 문맥에 있는 내용만 사용해서 대답해라.
    - 문맥에 없는 내용을 상상으로 만들지 마라.
    - '감사합니다', '경청해주셔서' 같은 인사 슬라이드는 무시해라.
    - 한국어로 답변해라.
    - 결과는 Markdown 형식으로 작성해라.

    [출력 형식 - 반드시 이 순서로, Markdown]

    ## 1. 전체 PPT 2줄 요약
    - 이 PPT 전체 내용을 한 문장으로 요약해라. (1줄)
    - 이 PPT의 핵심 포인트를 한 문장으로 다시 요약해라. (1줄)

    ## 2. 페이지별 학습용 상세 요약 (최대 8페이지)
    - 각 페이지마다 학생이 시험 공부할 때 볼 수 있도록,
      개념/정의/예시/주의점까지 포함해서 비교적 자세히 요약해라.
    - 필요하면 간단한 순서/단계도 함께 정리해라.

    각 페이지는 아래 형식을 따라라:

    ### 페이지 N 요약
    - [핵심 개념] 이 페이지에서 다루는 핵심 개념을 1~2문장으로 정리해라.
    - [설명] 그림, 표, 예시가 있다면 그것이 무엇을 보여주는지 2~4문장으로 설명해라.
    - [예시·절차] 계산 예시나 알고리즘이 있다면 중요한 단계 위주로 2~4문장으로 정리해라.
    - [시험 포인트] 시험에서 이 페이지와 관련해 반드시 기억해야 하는 포인트를 1~2줄로 정리해라.

    페이지 번호 N은 실제 [페이지 N]에 맞게 번호를 맞춰라.
    존재하지 않는 페이지 번호는 만들지 마라.

    ## 3. 페이지별 연습문제 (각 페이지당 2문제)
    - 각 페이지마다 2개의 연습문제를 만들어라.
    - 문제 유형은 객관식/단답형/서술형 중 아무거나 사용해도 되지만,
      반드시 해당 페이지 문맥에 실제로 등장한 개념·용어·수식·규칙을 기반으로 만들어라.
    - 각 문제 아래에 정답 또는 "정답 핵심 키워드"를 반드시 한 줄로 적어라.

    각 페이지의 연습문제는 아래 형식을 따라라:

    ### 페이지 N 연습문제
    **Q1.** (문제 내용)
    - 정답: (또는 정답 핵심 키워드)

    **Q2.** (문제 내용)
    - 정답: (또는 정답 핵심 키워드)

    페이지 번호 N은 실제 [페이지 N]에 맞게 번호를 맞춰라.
    존재하지 않는 페이지 번호에 대한 연습문제는 만들지 마라.
    """

    return _call_gpt(prompt)
