# 코레일 자동 예매

KTX/무궁화호 등 코레일 열차 취소표 자동 예매 스크립트

## 기능

- 다중 구간/시간대 동시 검색
- 좌석 타입 선택 (일반실/특실/전체)
- 텔레그램 알림 (선택)
- 자동 세션 갱신
- **웹 UI** - 브라우저에서 설정 편집 및 실행, 실시간 로그 확인

## 설치

```bash
./setup.sh
```

> Python 3.10 이상 필요. venv 생성, 의존성 설치, korail2 라이브러리 패치가 자동으로 수행됩니다.

## 실행 방법

### 방법 1: 웹 UI (권장)

`코레일예매.command` 파일을 **더블클릭**하면 터미널이 열리고 브라우저에서 웹 UI가 자동으로 열립니다.

또는 터미널에서 직접 실행:

```bash
source venv/bin/activate
python web_ui.py
```

브라우저에서 `http://127.0.0.1:5000`으로 접속됩니다.

#### 웹 UI 화면 구성

**1. 로그인 설정**
- 코레일 ID/PW 입력
- 텔레그램 봇 토큰/Chat ID 입력 (선택)
- 저장 버튼으로 `.env` 파일에 반영

**2. 검색 조건 관리**
- 검색 조건을 테이블로 확인
- 추가/편집/삭제 버튼으로 `search_configs.json` 관리
- 날짜는 달력 선택, 시간은 드롭다운으로 간편 입력

**3. 예매 실행**
- 예매 시작 버튼 클릭으로 스크립트 실행
- 실시간 로그 스트리밍으로 진행 상황 확인
- 중지 버튼으로 언제든 종료 가능

### 방법 2: CLI 직접 실행

```bash
./run.sh
```

> `.env`와 `search_configs.json`을 직접 편집한 후 실행합니다.

## 설정 파일

### 환경 변수 (.env)

```
KORAIL_ID=회원번호or이메일or전화번호
KORAIL_PW=비밀번호
TELEGRAM_BOT_TOKEN=봇토큰 (선택)
TELEGRAM_CHAT_ID=채팅ID (선택)
```

### 검색 조건 (search_configs.json)

```json
[
  {
    "dep_station": "서울",
    "arr_station": "부산",
    "dep_date": "20260214",
    "dep_time": "070000",
    "train_type": "KTX",
    "time_start": "07",
    "time_end": "10",
    "seat_type": "general"
  }
]
```

| 필드 | 설명 | 예시 |
|------|------|------|
| dep_station | 출발역 | 서울 |
| arr_station | 도착역 | 부산 |
| dep_date | 출발 날짜 (YYYYMMDD) | 20260214 |
| dep_time | 검색 시작 시간 (HHMMSS) | 070000 |
| train_type | 열차 종류 | KTX, MUGUNGHWA, ALL |
| time_start | 선호 시간대 시작 (HH) | 07 |
| time_end | 선호 시간대 종료 (HH) | 10 |
| seat_type | 좌석 종류 | general, special, any |

## 파일 구조

```
├── 코레일예매.command   # 더블클릭 실행 파일 (macOS)
├── web_ui.py            # 웹 UI 서버 (Flask)
├── auto_reserve_advanced.py  # 자동 예매 스크립트
├── search_configs.json  # 검색 조건 설정
├── .env                 # 로그인/텔레그램 설정 (gitignore)
├── .env.example         # .env 템플릿
├── run.sh               # CLI 실행 스크립트
├── setup.sh             # 설치 스크립트
└── requirements.txt     # 의존성 목록
```

## 주의사항

- 예약 성공 후 **20분 내 결제** 필요
- 코레일 앱 또는 홈페이지에서 결제 완료
- 웹 UI 서버는 로컬(127.0.0.1)에서만 접근 가능
