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
    generate_single_page_summary,  # 👈 새로 추가
)


st.set_page_config(page_title="Study-Mate", page_icon="📚", layout="wide")

st.title("📚 Study-Mate")
st.write("PDF 강의자료 기반으로 요약 · 페이지별 요약 · 문제 생성 · 채점 기능을 제공합니다!")

# -------------------------------------------------------------------
# 업로드 저장 디렉토리
# -------------------------------------------------------------------
UPLOAD_DIR = Path("data/uploaded")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

uploaded_file = st.file_uploader("강의자료 PDF 업로드", type=["pdf"])


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

# -------------------------------------------------------------------
# Session State 초기화
# -------------------------------------------------------------------
for key in [
    "whole_summary_output",
    "page_summary_output",
    "question_markdown",
    "question_answers",
]:
    if key not in st.session_state:
        st.session_state[key] = None


# ===================================================================
# PDF 처리 로직
# ===================================================================
if uploaded_file is not None:

    # 1) 파일 저장
    save_path = UPLOAD_DIR / uploaded_file.name
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"업로드 완료: {uploaded_file.name}")

    # 2) PDF 텍스트 추출
    with st.spinner("PDF에서 텍스트 추출 중..."):
        pages = extract_text_from_pdf(save_path)
    # st.success(f"텍스트 추출 완료! (총 {len(pages)} 페이지)")
    
        # 2-1) 페이지 이미지 추출 (앞 8페이지까지)
    with st.spinner("페이지 이미지를 불러오는 중입니다..."):
        page_images = load_page_images(str(save_path), max_pages=8)


    # 3) RAG용 청크 생성
    with st.spinner("벡터DB 저장 준비 중..."):
        chunks = split_pages_to_chunks(pages, chunk_size=300, overlap=80)
        add_chunks(chunks, source_name=uploaded_file.name)
    # st.success("벡터DB 저장 완료!")

    st.markdown("---")

    # ==============================================================
    # 🚀 3개의 탭 UI
    # ==============================================================
    tab1, tab2, tab3 = st.tabs(
        ["📘 전체 강의 요약", "📄 페이지별 자세한 요약", "📝 문제 생성 + 자동 채점"]
    )

    # ===================================================================
    # 📘 탭1: 전체 요약
    # ===================================================================
    with tab1:
        st.subheader("📘 전체 강의 요약 ")

        if st.button("👉 전체 강의 요약 생성하기"):
            with st.spinner("전체 요약 생성 중..."):
                try:
                    st.session_state.whole_summary_output = generate_whole_summary(pages)
                except RuntimeError as e:
                    st.error("❌ 오류 발생")
                    st.code(repr(e))

        if st.session_state.whole_summary_output:
            st.markdown("📘 전체 요약 결과")
            st.markdown(st.session_state.whole_summary_output)



    # ===================================================================
    # 📄 탭2: 페이지별 상세 요약
    # ===================================================================
    # ===================================================================
    # 📄 탭2: 페이지별 상세 요약 + 이미지
    # ===================================================================
    # ===================================================================
    # 📄 탭2: 페이지별 상세 요약 + 이미지 (가독성 개선 버전)
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
        )

        # 요약 상태 저장용
        if "single_page_summary" not in st.session_state:
            st.session_state.single_page_summary = ""

        # 2열 레이아웃: 왼쪽 이미지, 오른쪽 요약 카드
        col_img, col_text = st.columns([1, 1.1], gap="large")

        with col_img:
            st.markdown(f"📘 페이지 {page_num} 미리보기")
            if len(page_images) >= page_num:
                # ⚠️ deprecated 된 use_column_width 대신 use_container_width 사용
                st.image(page_images[page_num - 1], width="stretch")
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
                # ----------- 🔧 Summary Clean-up (불필요한 마크다운 제거) -----------
                clean = summary_text

                # 헤더 제거
                clean = clean.replace("### 📘 페이지", "📘 페이지")
                clean = clean.replace("###", "")

                # "-**" 같은 이상한 조합 제거
                clean = clean.replace("-**", "")
                clean = clean.replace("**-", "")

                # "**개념**" 같은 부분 이쁘게 바꾸기
                clean = clean.replace("**[개념]**", "📘 개념")
                clean = clean.replace("**[설명]**", "📝 설명")
                clean = clean.replace("**[예시/절차]**", "🔍 예시/절차")
                clean = clean.replace("**[시험 포인트]**", "📌 시험 포인트")

                # ── 라벨과 내용을 분리해서 가독성 높이기 ──
                clean = clean.replace("- 📘 개념 ", "📘 개념<br>")
                clean = clean.replace("- 📝 설명 ", "<br><br>📝 설명<br>")
                clean = clean.replace("- 🔍 예시/절차 ", "<br><br>🔍 예시/절차<br>")
                clean = clean.replace("- 📌 시험 포인트 ", "<br><br>📌 시험 포인트<br>")

                # 남은 ** 전부 제거
                clean = clean.replace("**", "")


                # 줄바꿈 → <br> 로
                html_text = clean.replace("\n", "<br>")

                # ----------- 🍏 아이패드 노트 스타일 카드 -----------
                st.markdown(
                    """
                    <style>
                        .ipad-note {{
                            background-color: #FAF9F7;
                            color: #1A1A1A;
                            padding: 28px 30px;
                            border-radius: 22px;
                            border: 1px solid #E5E0D8;
                            width: 100%;                    /* 🔥 전체 폭 사용 */
                            box-shadow:
                                0px 4px 14px rgba(0,0,0,0.06),
                                0px 12px 32px rgba(0,0,0,0.08);   /* 🔥 더 부드러운 그림자 */
                            line-height: 1.95;              /* 🔥 더 넓은 줄간격 */
                            font-size: 1.05rem;             /* 살짝 크게 */
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
    # ===================================================================
    # 📝 탭3: 문제 생성 + 자동 채점
    # ===================================================================
    with tab3:
        st.subheader("📝 페이지별 문제 생성 (각 페이지당 2문제)")

        difficulty = st.selectbox(
            "난이도 선택",
            ["easy", "medium", "hard"],
            index=1
        )

        if "question_list" not in st.session_state:
            st.session_state.question_list = []

        if st.button("👉 문제 생성하기"):
            with st.spinner("문제 생성 중..."):
                try:
                    questions = generate_page_questions(pages, difficulty=difficulty)
                    st.session_state.question_list = questions
                except RuntimeError as e:
                    st.error("❌ 문제 생성 중 오류 발생")
                    st.code(repr(e))

        questions = st.session_state.question_list

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
        else:
            st.info("먼저 문제를 생성해 주세요.")




else:
    st.info("왼쪽 상단에서 PDF 파일을 업로드해 주세요.")
