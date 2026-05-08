# 💰 MH Pension App (Streamlit MVP)

펜션 포트폴리오 시각화 웹앱. 노션을 데이터 소스로 사용.

## 🚀 빠른 시작

### 1. 환경 설정 (한 번만)

```bash
cd ~/Desktop/01_MH_Finance/03_Asset_App
source venv/bin/activate
```

> ✅ 가상환경(`venv/`)과 패키지는 이미 설치되어 있음.

### 2. `.env` 파일 생성 (한 번만)

```bash
cp .env.example .env
```

그 다음 `.env` 파일을 텍스트 편집기로 열어 `NOTION_TOKEN` 줄에 노션 통합 토큰을 붙여넣고 저장.

> **토큰 위치**: https://www.notion.so/my-integrations → **MH Pension App** → Internal Integration Token

### 3. 앱 실행

```bash
source venv/bin/activate
streamlit run app.py
```

자동으로 브라우저가 `http://localhost:8501` 열림.

### 4. 종료

터미널에서 `Ctrl+C`.

---

## 📱 모바일에서 보기

같은 Wi-Fi 네트워크에서:

1. 위 명령 실행 후 터미널에 표시되는 **Network URL** 확인 (예: `http://192.168.0.100:8501`)
2. 휴대폰 사파리/크롬 주소창에 입력
3. 사파리 → 공유 → "홈 화면에 추가" → 앱처럼 사용

---

## 📂 프로젝트 구조

```
03_Asset_App/
├── app.py                          # 홈 (KPI 대시보드)
├── pages/
│   ├── 1_📊_Holdings.py           # 보유 종목 + 필터 + 히트맵
│   ├── 2_💸_Cashflow.py           # 12개월 분배 추이
│   └── 3_🎯_Buy_Strategy.py       # 매수 가이드 + 시뮬레이터
├── lib/
│   ├── notion.py                   # 노션 API 클라이언트
│   └── transform.py                # 데이터 변환
├── .env                            # 토큰 (gitignore 됨)
├── .env.example                    # 템플릿
├── .streamlit/config.toml          # 테마
├── requirements.txt
└── README.md
```

---

## 🔄 데이터 갱신

- **자동**: 5분 캐시 (Streamlit `@st.cache_data`)
- **수동**: 홈 화면 우상단 **🔄 새로고침** 버튼

노션에서 직접 데이터 입력하면 5분 후 자동 반영. 즉시 보고 싶으면 새로고침.

---

## 📦 의존성

- Python 3.9+
- streamlit 1.50+
- notion-client 2.2+
- plotly 6.0+
- pandas 2.0+
- python-dotenv 1.0+

---

## 🎯 추후 업그레이드 예정

- Node.js 설치 후 → **Next.js + Vercel 배포**로 마이그레이션
- 일반 주식 트랙 추가 (Trades / Positions / Watchlist DB 연동)
- 변동성 시계열 차트 (월별 자동 동기화 누적 후)
- PWA 푸시 알림 (분배일 알림)

---

## 🐛 문제 해결

### "노션 연결 실패"
- `.env` 파일에 `NOTION_TOKEN`이 정확히 입력되어 있는지 확인
- 토큰을 재발급한 적이 있다면 `.env` 갱신
- 노션 통합이 페이지에 추가되어 있는지 확인 (Content access 탭)

### "Module not found"
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 캐시 문제
홈 화면 🔄 새로고침 버튼 클릭 또는 앱 재시작.
