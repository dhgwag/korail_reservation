# 기차표 자동 예매 (코레일 / SRT)

코레일(KTX/무궁화 등) + SRT 취소표 자동 예매 스크립트. 한 웹 UI에서 탭을 전환하며 두 서비스를 동시에 운영할 수 있습니다.

## 기능

- 코레일 / SRT 각각 독립적인 검색·예매 루프
- 다중 구간/시간대 동시 검색
- 좌석 타입 선택 (일반실 / 특실 / 전체)
- 텔레그램 알림 (선택)
- 자동 세션 갱신 & 재로그인
- **웹 UI** — 브라우저에서 설정 편집, 탭 전환, 실시간 로그 확인
- SRT 휴대폰 ID 하이픈 자동 정규화 (`01012345678` → `010-1234-5678`)

## 설치

```bash
./setup.sh
```

> Python 3.10 이상 필요. venv 생성, 의존성 설치(코레일/SRT 라이브러리 fork 포함), korail2 패치가 자동으로 수행됩니다.

## 실행 방법

### 방법 1: 웹 UI (권장)

`기차표예매.command` 파일을 **더블클릭**하면 터미널이 열리고 브라우저에서 웹 UI가 자동으로 열립니다.

또는 터미널에서 직접:

```bash
source venv/bin/activate
python web_ui.py
```

브라우저에서 `http://127.0.0.1:5001`로 접속됩니다.

> 포트 5000은 macOS의 AirPlay 수신기가 선점하므로 기본값은 5001입니다. 변경하려면 `WEB_UI_PORT=8080 python web_ui.py`.

#### 웹 UI 화면 구성

**1. 로그인 설정 (공용)**
- 코레일 ID/PW
- SRT ID/PW
- 텔레그램 봇 토큰 / Chat ID (선택)
- 저장 버튼으로 `.env` 파일에 반영

**2. 서비스 탭 (코레일 / SRT)**
- 탭 전환으로 서비스별 화면 이동
- 각 탭마다 검색 조건 테이블 + 실행 패널
- 탭 버튼 옆 미니 상태점이 현재 실행 여부 표시

**3. 검색 조건 관리**
- 추가/편집/삭제 버튼으로 `korail_configs.json` / `srt_configs.json` 관리
- SRT 탭에서는 열차 종류 선택이 숨겨집니다 (항상 SRT)

**4. 예매 실행**
- 예매 시작 버튼 클릭으로 각 서비스 스크립트 실행
- 실시간 로그 스트리밍 (SSE)
- 중지 버튼으로 언제든 종료

### 방법 2: CLI 직접 실행

```bash
./run.sh korail   # 코레일
./run.sh srt      # SRT
```

> `.env`와 `*_configs.json`을 직접 편집한 후 실행합니다.

## 설정 파일

### 환경 변수 (.env)

```
KORAIL_ID=회원번호or이메일or전화번호
KORAIL_PW=비밀번호
SRT_ID=회원번호or이메일or전화번호
SRT_PW=비밀번호
TELEGRAM_BOT_TOKEN=봇토큰 (선택)
TELEGRAM_CHAT_ID=채팅ID (선택)
```

### 검색 조건

**코레일 (`korail_configs.json`)**

```json
[
  {
    "dep_station": "서울",
    "arr_station": "부산",
    "dep_date": "20260428",
    "dep_time": "070000",
    "train_type": "KTX",
    "time_start": "07",
    "time_end": "10",
    "seat_type": "general"
  }
]
```

**SRT (`srt_configs.json`)**

```json
[
  {
    "dep_station": "수서",
    "arr_station": "울산(통도사)",
    "dep_date": "20260430",
    "dep_time": "050000",
    "time_start": "05",
    "time_end": "07",
    "seat_type": "general"
  }
]
```

| 필드 | 설명 | 예시 |
|------|------|------|
| dep_station | 출발역 (정확 명칭) | 서울 / 수서 |
| arr_station | 도착역 (정확 명칭) | 부산 / 울산(통도사) |
| dep_date | 출발 날짜 (YYYYMMDD) | 20260428 |
| dep_time | 검색 시작 시각 (HHMMSS) | 070000 |
| train_type | 열차 종류 (**코레일 전용**) | KTX / MUGUNGHWA / ALL |
| time_start | 선호 시간대 시작 (HH) | 07 |
| time_end | 선호 시간대 종료 (HH) | 10 |
| seat_type | 좌석 종류 | general / special / any |

> **SRT 역명 주의**: SRT는 "울산(통도사)", "동대구" 등 정식 명칭을 요구합니다. "울산"처럼 짧게 쓰면 `Station not exists` 오류가 납니다.

## 파일 구조

```
├── 기차표예매.command       # 더블클릭 실행 (macOS)
├── web_ui.py                # 웹 UI 서버 (Flask, 탭 + 듀얼 프로세스)
├── auto_reserve_korail.py   # 코레일 자동 예매
├── auto_reserve_srt.py      # SRT 자동 예매
├── korail_configs.json      # 코레일 검색 조건
├── srt_configs.json         # SRT 검색 조건
├── .env                     # 로그인/텔레그램 설정 (gitignore)
├── .env.example             # .env 템플릿
├── run.sh                   # CLI 실행 (./run.sh korail|srt)
├── setup.sh                 # 설치 스크립트
└── requirements.txt         # 의존성 (korail2, SRTrain 포크 포함)
```

## 의존 라이브러리

- [dhgwag/korail2](https://github.com/dhgwag/korail2) (fork of [carpedm20/korail2](https://github.com/carpedm20/korail2), 안티봇 우회 패치)
- [dhgwag/SRT](https://github.com/dhgwag/SRT) (fork of [ryanking13/SRT](https://github.com/ryanking13/SRT))
- Flask, requests

## 주의사항

- 예약 성공 후 **20분 내 결제** 필요
- 결제는 코레일/SRT 앱 또는 홈페이지에서 직접
- 웹 UI 서버는 로컬(`127.0.0.1`)에서만 접근
- SRT 휴대폰 번호 ID는 하이픈 있어야 인식됩니다 (스크립트가 자동 보정하지만, UI 입력 시 `010-1234-5678` 권장)
