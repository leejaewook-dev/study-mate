import streamlit as st
from pathlib import Path
import fitz  # PDF → 이미지 변환용

from utils.extract_pdf import extract_text_from_pdf
from utils.chunker import split_pages_to_chunks
from utils.chroma_db import add_chunks, query_similar

# Gemini LLM
from utils.llm_gemini import (
    generate_whole_summary,
    generate_page_summaries,   # (원래꺼 써도 되고, 나중에 안쓰면 지워도 됨)
    generate_page_questions,
    generate_single_page_summary,
)

# -------------------------------------------------------------------
# 기본 설정
# -------------------------------------------------------------------
st.set_page_config(page_title="Study-Mate", page_icon="📚", layout="wide")

st.title("📚 Study-Mate")
st.write("PDF 강의자료 기반으로 요약 · 페이지별 요약 · 문제 생성 · 채점 기능을 제공합니다!")

# -------------------------------------------------------------------
# 업로드 저장 디렉토리
# -------------------------------------------------------------------
UPLOAD_DIR = Path("data/uploaded")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# Session State 초기화 (학습 진도/로그 + 요약/문제 상태)
# -------------------------------------------------------------------
# 학습 진도 / 로그 관리용
if "study_progress" not in st.session_state:
    # pdf_name -> {"completed": bool, "correct": int, "total": int}
    st.session_state.study_progress = {}

if "total_pdfs" not in st.session_state:
    st.session_state.total_pdfs = 5  # 기본값 (사이드바에서 조정할 수도 있음)

# 현재 선택된 PDF 이름
if "current_pdf_name" not in st.session_state:
    st.session_state.current_pdf_name = None

# 요약/문제 관련 상태
for key in [
    "whole_summary_output",
    "single_page_summary",
    "question_list",
    "page_summary_output",
    "question_markdown",
    "question_answers",
]:
    if key not in st.session_state:
        st.session_state[key] = "" if key == "single_page_summary" else None

# -------------------------------------------------------------------
# 유틸 함수: PDF → 이미지
# -------------------------------------------------------------------
def load_page_images(pdf_path: str, max_pages: int = 8):
    """
    PDF 파일에서 앞쪽 max_pages개의 페이지를 PNG 이미지(bytes)로 뽑아오는 함수
    """
    doc = fitz.open(pdf_path)
    images = []
    try:
        for i in range(min(max_pages, len(doc))):
            page = doc.load_page(i)
            # 배율 2배로 조금 더 선명하게
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            images.append(img_bytes)
    finally:
        doc.close()
    return images

# 과목명 입력
course_name = st.text_input(
    "과목명을 입력하세요 (예: 컴퓨터구조)",
    key="course_name",
    placeholder="예: 컴퓨터구조, 딥러닝 개론 등"
)

# ===================================================================
# 📂 여러 개 PDF 업로드
# ===================================================================
uploaded_files = st.file_uploader(
    "📄 시험 범위 PDF 업로드 (여러 개 선택 가능)",
    type=["pdf"],
    accept_multiple_files=True,
)

# ===================================================================
# 📚 업로드가 아직 없을 때 사이드바 (간단 안내)
# ===================================================================
if not uploaded_files:
    with st.sidebar:
        if course_name:
            st.subheader(f"📚 {course_name} 시험 진도")
        else:
            st.subheader("📚 과목명을 먼저 입력하세요")

        st.info("시험 범위 PDF를 업로드하면 진도가 자동으로 표시됩니다.")
    # 메인 영역 안내
    st.info("위에서 시험 범위에 해당하는 PDF 파일들을 업로드해 주세요. (여러 개 선택 가능)")
    st.stop()  # 아래 코드 실행하지 않음

# ===================================================================
# 메인 영역: PDF 선택 → 요약/문제 기능
# ===================================================================
if uploaded_files:

    # 1) 지금 공부할 PDF 선택
    file_names = [f.name for f in uploaded_files]
    current_pdf_name = st.selectbox(
        "지금 공부할 PDF를 선택하세요",
        options=file_names,
    )

    # 선택된 이름과 일치하는 UploadedFile 찾기
    current_pdf = next(f for f in uploaded_files if f.name == current_pdf_name)

    # 🔄 PDF가 바뀌면 요약/문제 상태 초기화
    if st.session_state.current_pdf_name != current_pdf_name:
        st.session_state.current_pdf_name = current_pdf_name
        st.session_state.whole_summary_output = None
        st.session_state.single_page_summary = ""
        st.session_state.question_list = []

    # 2) 파일 저장
    save_path = UPLOAD_DIR / current_pdf_name
    with open(save_path, "wb") as f:
        f.write(current_pdf.getbuffer())
    st.success(f"업로드 완료: {current_pdf_name}")

    # 3) PDF 텍스트 추출
    with st.spinner("PDF에서 텍스트 추출 중..."):
        pages = extract_text_from_pdf(save_path)

    # 3-1) 페이지 이미지 추출 (앞 8페이지까지)
    with st.spinner("페이지 이미지를 불러오는 중입니다..."):
        page_images = load_page_images(str(save_path), max_pages=8)

    # 4) RAG용 청크 생성
    with st.spinner("벡터DB 저장 준비 중..."):
        chunks = split_pages_to_chunks(pages, chunk_size=300, overlap=80)
        add_chunks(chunks, source_name=current_pdf_name)

    # ===================================================================
    # 📚 사이드바: 과목명 + 자동 진도 + 전체 학습 로그
    # ===================================================================
    # ===================================================================
    # 📚 사이드바: 과목명 + 현재 PDF 진도 + 전체 과목 진도
    # ===================================================================
    with st.sidebar:
        # 1) 제목: 과목명 + "시험 진도"
        if course_name:
            st.subheader(f"📄 현재 PDF 진행 상황")
        else:
            st.subheader("📚 과목명을 먼저 입력하세요")

        # 2) 현재 선택된 PDF 기준 진도 (페이지 단위)
        total_pages = len(pages)
        current_page = st.session_state.get("page_index", 1)
        current_page = max(1, min(current_page, total_pages))  # 안전 조정


        pdf_ratio = current_page / total_pages
        st.progress(pdf_ratio)
        st.write(f"- 현재 페이지: **{current_page} / {total_pages}**")
        st.caption(f"→ 현재 PDF의 약 {pdf_ratio * 100:.1f}%를 학습했습니다.")

        st.markdown("---")

        # 3) 과목 전체 진도 (완료한 PDF 개수 / 업로드한 PDF 개수)
        progress_dict = st.session_state.study_progress   # 채점 후 기록되는 dict
        uploaded_count = len(uploaded_files)              # 이번 과목에서 업로드한 PDF 개수
        completed_count = sum(
            1 for v in progress_dict.values() if v.get("completed")
        )

        overall_ratio = (completed_count / uploaded_count) if uploaded_count else 0.0

        if course_name:
            st.markdown(f"### 📊 {course_name} 전체 진도율")
        else:
            st.markdown("### 📊 전체 진도율")

        st.progress(overall_ratio)
        st.write(f"- 완료한 PDF: **{completed_count} / {uploaded_count} 개**")
        st.caption(
            "→ ‘완료’는 문제를 풀고 채점까지 끝낸 PDF 기준으로 집계합니다."
        )

        # 4) 학습 로그 (PDF별 상태/점수)
        if progress_dict:
            st.markdown("### 📘 학습 로그")
            for pdf_name, info in progress_dict.items():
                completed = "✅ 완료" if info.get("completed") else "⏳ 진행 중"
                correct = info.get("correct", 0)
                total_q = info.get("total", 0)
                score_text = f"{correct}/{total_q}" if total_q else "-"

                st.markdown(
                    f"- **{pdf_name}**  \n"
                    f"  • 상태: {completed}  \n"
                    f"  • 점수: {score_text}"
                )
        else:
            st.info("아직 학습 기록이 없습니다. 문제를 풀고 채점하면 여기에 기록돼요.")


    # ==============================================================  
    # 🚀 3개의 탭 UI
    # ==============================================================  
    tab1, tab2, tab3 = st.tabs(
        ["📘 전체 강의 요약", "📄 페이지별 자세한 요약", "📝 연습 문제 생성"]
    )

    # ===================================================================
    # 📘 탭1: 전체 요약
    # ===================================================================
    with tab1:
        st.subheader("📘 전체 강의 요약 ")

        # 🔥 스타일 적용 (iPad 노트 스타일)
        st.markdown(
            """
            <style>
                .ipad-note {
                    background-color: #FAF9F7;
                    color: #1A1A1A;
                    padding: 28px 30px;
                    border-radius: 22px;
                    border: 1px solid #E5E0D8;
                    width: 100%;
                    box-shadow:
                        0px 4px 14px rgba(0,0,0,0.06),
                        0px 12px 32px rgba(0,0,0,0.08);
                    line-height: 1.95;
                    font-size: 1.05rem;
                    font-weight: 600;
                    letter-spacing: -0.15px;
                }
            </style>
            """,
            unsafe_allow_html=True
        )

        if st.button("👉 전체 강의 요약 생성하기"):
            with st.spinner("전체 요약 생성 중..."):
                try:
                    st.session_state.whole_summary_output = generate_whole_summary(pages)
                except RuntimeError as e:
                    st.error("❌ 오류 발생")
                    st.code(repr(e))

        if st.session_state.whole_summary_output:
            st.markdown("📘 전체 요약 결과")
            st.markdown(
                f"""
                <div class="ipad-note">
                    {st.session_state.whole_summary_output}
                </div>
                """,
                unsafe_allow_html=True
            )

    # ===================================================================
    # 📄 탭2: 페이지별 상세 요약 + 이미지
    # ===================================================================
    with tab2:
        st.subheader("📄 페이지별 상세 요약 (이미지 + 텍스트)")

        max_page_for_summary = min(8, len(pages))
        page_num = st.number_input(
            "요약할 페이지 선택 (1~8페이지까지만 지원)",
            min_value=1,
            max_value=max_page_for_summary,
            value=1,
            step=1,
            key="page_index",   # 👉 사이드바 진도와 연결되는 key
        )

        # 2열 레이아웃: 왼쪽 이미지, 오른쪽 요약 카드
        col_img, col_text = st.columns([1, 1.1], gap="large")

        with col_img:
            st.markdown(f"📘 페이지 {page_num} 미리보기")
            if len(page_images) >= page_num:
                st.image(page_images[page_num - 1], use_container_width=True)
            else:
                st.info("이미지 정보가 없습니다.")

        with col_text:
            st.markdown(f"📘 페이지 {page_num} 학습용 요약")

            if st.button("👉 이 페이지 요약 생성하기", key=f"summary_page_{page_num}"):
                with st.spinner("해당 페이지를 요약하는 중입니다..."):
                    try:
                        summary = generate_single_page_summary(
                            pages[page_num - 1],
                            page_number=page_num,
                        )
                        st.session_state.single_page_summary = summary
                    except RuntimeError as e:
                        st.error("❌ 페이지 요약 중 오류 발생")
                        st.code(repr(e))

            summary_text = st.session_state.get("single_page_summary", "")

            if summary_text:
                clean = summary_text
                clean = clean.replace("### 📘 페이지", "📘 페이지")
                clean = clean.replace("###", "")
                clean = clean.replace("-**", "")
                clean = clean.replace("**-", "")
                clean = clean.replace("**[개념]**", "📘 개념")
                clean = clean.replace("**[설명]**", "📝 설명")
                clean = clean.replace("**[예시/절차]**", "🔍 예시/절차")
                clean = clean.replace("**[시험 포인트]**", "📌 시험 포인트")
                clean = clean.replace("- 📘 개념 ", "📘 개념<br>")
                clean = clean.replace("- 📝 설명 ", "<br><br>📝 설명<br>")
                clean = clean.replace("- 🔍 예시/절차 ", "<br><br>🔍 예시/절차<br>")
                clean = clean.replace("- 📌 시험 포인트 ", "<br><br>📌 시험 포인트<br>")
                clean = clean.replace("**", "")
                html_text = clean.replace("\n", "<br>")

                st.markdown(
                    """
                    <style>
                        .ipad-note {{
                            background-color: #FAF9F7;
                            color: #1A1A1A;
                            padding: 28px 30px;
                            border-radius: 22px;
                            border: 1px solid #E5E0D8;
                            width: 100%;
                            box-shadow:
                                0px 4px 14px rgba(0,0,0,0.06),
                                0px 12px 32px rgba(0,0,0,0.08);
                            line-height: 1.95;
                            font-size: 1.05rem;
                            font-weight: 600;
                            letter-spacing: -0.15px;
                        }}
                    </style>

                    <div class="ipad-note">
                        {}
                    </div>
                    """.format(html_text),
                    unsafe_allow_html=True,
                )
            else:
                st.info("오른쪽 위 버튼을 눌러 이 페이지 요약을 생성해 보세요.")

    # ===================================================================
    # 📝 탭3: 문제 생성 + 자동 채점
    # ===================================================================
    with tab3:
        st.subheader("📝 페이지별 문제 생성")

        total_pages = len(pages)
        page_numbers = list(range(1, total_pages + 1))

        selected_pages = st.multiselect(
            "문제 출제를 원하는 페이지를 선택하세요 (여러 개 선택 가능)",
            options=page_numbers,
            default=page_numbers,
        )

        num_questions = st.number_input(
            "페이지당 생성할 문제 개수",
            min_value=1,
            max_value=5,
            value=2,
            step=1,
        )

        difficulty = st.selectbox(
            "난이도 선택",
            ["easy", "medium", "hard"],
            index=1,
        )

        if "question_list" not in st.session_state or st.session_state.question_list is None:
            st.session_state.question_list = []

        if st.button("👉 문제 생성하기"):
            if not selected_pages:
                st.warning("먼저 문제를 출제할 페이지를 한 개 이상 선택하세요.")
            else:
                with st.spinner("문제 생성 중..."):
                    try:
                        questions = generate_page_questions(
                            pages=pages,
                            selected_pages=selected_pages,
                            num_questions=num_questions,
                            difficulty=difficulty,
                        )
                        st.session_state.question_list = questions
                    except RuntimeError as e:
                        st.error("❌ 문제 생성 중 오류 발생")
                        st.code(repr(e))

        questions = st.session_state.question_list or []

        if questions:
            st.markdown("📝 생성된 문제")

            for q in questions:
                qid = q.get("id", "Q")
                page_no = q.get("page", "?")
                question_text = q.get("question", "")
                choices = q.get("choices", {})
                correct_idx = str(q.get("answer", ""))

                st.markdown(f"**[{qid}] (페이지 {page_no})** {question_text}")

                for num, text in choices.items():
                    st.markdown(f"{num}) {text}")

                st.radio(
                    "정답 선택",
                    options=["1", "2", "3", "4"],
                    key=f"answer_{qid}",
                    horizontal=True,
                    label_visibility="collapsed",
                )

                st.markdown("---")

            if st.button("채점하기"):
                correct_count = 0
                st.markdown("📊 채점 결과")

                for q in questions:
                    qid = q.get("id", "Q")
                    correct = str(q.get("answer", ""))
                    user = st.session_state.get(f"answer_{qid}", None)

                    if user == correct:
                        st.success(f"{qid}: 정답! ✔ (선택: {user}, 정답: {correct})")
                        correct_count += 1
                    else:
                        st.error(f"{qid}: 오답 ❌ (선택: {user}, 정답: {correct})")

                    explain = q.get("explain", "")
                    if explain:
                        st.caption(f"해설: {explain}")

                st.markdown(f"## ✅ 총 점수: **{correct_count} / {len(questions)}**")

                if current_pdf_name is not None:
                    progress_dict = st.session_state.study_progress
                    progress_dict[current_pdf_name] = {
                        "completed": True,
                        "correct": correct_count,
                        "total": len(questions),
                    }
                    st.session_state.study_progress = progress_dict

                    st.success(
                        f"📌 '{current_pdf_name}' 학습 완료로 기록되었습니다! "
                        "사이드바에서 전체 진도율과 학습 로그를 확인할 수 있어요."
                    )
        else:
            st.info("먼저 문제를 생성해 주세요.")
