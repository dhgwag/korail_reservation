# 코레일 자동 예매

KTX/무궁화호 등 코레일 열차 취소표 자동 예매 스크립트

## 기능

- 다중 구간/시간대 동시 검색
- 좌석 타입 선택 (일반실/특실/전체)
- 텔레그램 알림 (선택)
- 자동 세션 갱신

## 설치

```bash
./setup.sh
```

## 설정

### 1. 환경 변수 (.env)

```
KORAIL_ID=회원번호or이메일or전화번호
KORAIL_PW=비밀번호
TELEGRAM_BOT_TOKEN=봇토큰 (선택)
TELEGRAM_CHAT_ID=채팅ID (선택)
```

### 2. 검색 조건 (search_configs.json)

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

| 필드 | 설명 |
|------|------|
| dep_station | 출발역 |
| arr_station | 도착역 |
| dep_date | 출발 날짜 (YYYYMMDD) |
| dep_time | 검색 시작 시간 (HHMMSS) |
| train_type | KTX, MUGUNGHWA, ALL |
| time_start | 선호 시간대 시작 (HH) |
| time_end | 선호 시간대 종료 (HH) |
| seat_type | general, special, any |

## 실행

```bash
./run.sh
```

## 주의사항

- 예약 성공 후 **20분 내 결제** 필요
- 코레일 앱 또는 홈페이지에서 결제 완료
