# studt-mate-
RAG 기반 PDF 요약 &amp; 문제 생성 시스템
# 📚 Study-Mate  
PDF 기반 강의자료 요약 · 페이지별 상세 요약 · 문제 생성 · 자동 채점 · 학습 진도 관리

AI 기반 학습 보조도구 **Study-Mate**는 대학 강의 PDF(PPT)를 업로드하면  
✨ **전체 강의 요약**,  
✨ **페이지별 상세 요약(이미지 포함)**,  
✨ **페이지 단위 문제 생성 및 자동 채점**,  
✨ **학습 진도 자동 관리**,  
✨ **RAG 기반 문맥 검색(옵션)**  
기능을 제공합니다.

---

## 🧠 주요 기능 Overview

### 1) 📘 **전체 강의 요약**
- PDF 전체 페이지의 텍스트를 분석해 핵심 내용을 정리
- 요약은 “도입 → 핵심 개념 → 정리” 형태로 8~15 문장 구성
- iPad 노트 스타일 UI로 읽기 쉬운 출력

---

### 2) 📄 **페이지별 상세 요약 (이미지 + 텍스트)**
- PDF 앞 8페이지까지 이미지로 렌더링해 미리보기 제공
- 각 페이지의 핵심 개념을 구조화하여 요약
- 개념/설명/예시/시험 포인트 등 포맷 유지
- HTML 변환으로 깔끔한 학습 카드 UI 제공

---

### 3) 📝 **페이지별 문제 생성 + 자동 채점**
- 원하는 페이지 범위 선택 → 문제 자동 생성
- 객관식(4지선다), 난이도 조절(easy/medium/hard)
- 문제풀이 후 즉시 자동 채점
- 채점 결과는 학습 로그에 자동 기록됨

---

### 4) 📊 **학습 진도 자동 관리**
사이드바에서 2가지 진도 정보를 자동 계산하여 표시합니다:

#### ✔ 현재 PDF 진도  
- 현재 보고 있는 페이지 / 전체 페이지  
- Streamlit progress bar 표시

#### ✔ 전체 과목 진도  
- 업로드한 모든 PDF 중  
  **문제 풀이 + 채점 완료된 PDF 비율**
- 학습 로그에 각 PDF별 점수도 저장됨

---

### 5) 🔍 **RAG 기반 문맥 검색(선택 기능)**
- PDF 텍스트를 청크로 나눠 Chroma DB에 저장
- 사용자가 질문하면 의미적으로 가까운 문단 검색
- 검색된 문단 기반 요약/답변 생성 가능

---

## 🏗 기술 구조 (Architecture)

### 🔹 Frontend/UI : Streamlit  
- 탭 UI (전체 요약 / 페이지 요약 / 문제 생성)  
- 사이드바로 과목명 + 진도 관리  
- 이미지 + 텍스트 요약 카드의 iPad-style 스타일링

### 🔹 Backend  
- **Gemini 2.5 Flash** 모델 기반 요약/문제 생성  
- PDF → 텍스트 추출 : PyMuPDF(fitz)  
- PDF → 이미지 렌더링  
- 청크 기반 임베딩 → Chroma DB 저장 (RAG 옵션)

---

## 📦 프로젝트 폴더 구조
study-mate/
├── app.py # Streamlit 메인 앱
├── utils/
│ ├── extract_pdf.py # PDF 텍스트 추출
│ ├── chunker.py # 페이지 → 청크 분리
│ ├── chroma_db.py # Chroma DB 저장/검색
│ ├── llm_gemini.py # Gemini 요약/문제 생성 로직
│
├── chroma_db/ # (자동 생성, Git에 올리면 안됨)
├── data/
│ └── uploaded/ # PDF 업로드 저장 폴더
├── .gitignore
├── README.md
└── requirements.txt


---

## 🚀 실행 방법

### 1) 가상환경 생성 & 활성화
```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows

2) 필요한 패키지 설치
pip install -r requirements.txt

3) Gemini API Key 설정
GEMINI_API_KEY=너의_API_KEY

4) 앱 실행
streamlit run app.py
