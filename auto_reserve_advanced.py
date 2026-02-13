#!/usr/bin/env python3
"""
코레일 자동 예매 스크립트 (고급 버전)
- 다중 열차/시간대 검색
- 텔레그램 알림 기능
- 예매 성공 시 알림
"""

import time
import os
import json
import requests
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from korail2 import Korail, AdultPassenger, ChildPassenger, SeniorPassenger
from korail2 import ReserveOption, TrainType
from korail2 import NoResultsError, SoldOutError
from enum import Enum


class NeedReloginError(Exception):
    """로그인 세션 만료 시 발생하는 예외"""

    pass


class SeatType(Enum):
    """좌석 종류"""

    GENERAL = "general"  # 일반실만
    SPECIAL = "special"  # 특실만
    ANY = "any"  # 둘 다 가능 (먼저 잡히는 것)


@dataclass
class SearchConfig:
    """열차 검색 설정"""

    dep_station: str  # 출발역
    arr_station: str  # 도착역
    dep_date: str  # 출발 날짜 (YYYYMMDD)
    dep_time: str  # 출발 시간 (HHMMSS)
    train_type: str = TrainType.KTX
    time_start: Optional[str] = None  # 선호 시작 시간 (HH)
    time_end: Optional[str] = None  # 선호 종료 시간 (HH)
    seat_type: SeatType = SeatType.ANY  # 좌석 종류 (특실/일반실/둘다)


# ============ 설정 ============

# 로그인 정보 (환경 변수 또는 직접 입력)
KORAIL_ID = os.environ.get("KORAIL_ID", "YOUR_ID")
KORAIL_PW = os.environ.get("KORAIL_PW", "YOUR_PASSWORD")

# 텔레그램 알림 설정 (선택사항)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# 검색 설정 파일 경로
SEARCH_CONFIGS_FILE = os.path.join(os.path.dirname(__file__), "search_configs.json")


def load_search_configs() -> list[SearchConfig]:
    """JSON 파일에서 검색 설정 로드"""
    with open(SEARCH_CONFIGS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    train_type_map = {
        "KTX": TrainType.KTX,
        "MUGUNGHWA": TrainType.MUGUNGHWA,
        "ALL": TrainType.ALL,
    }
    seat_type_map = {
        "general": SeatType.GENERAL,
        "special": SeatType.SPECIAL,
        "any": SeatType.ANY,
    }

    configs = []
    for item in data:
        configs.append(
            SearchConfig(
                dep_station=item["dep_station"],
                arr_station=item["arr_station"],
                dep_date=item["dep_date"],
                dep_time=item["dep_time"],
                train_type=train_type_map.get(
                    item.get("train_type", "KTX"), TrainType.KTX
                ),
                time_start=item.get("time_start"),
                time_end=item.get("time_end"),
                seat_type=seat_type_map.get(item.get("seat_type", "any"), SeatType.ANY),
            )
        )
    return configs


# 승객 정보
PASSENGERS = [
    AdultPassenger(1),
]

# 좌석 옵션
RESERVE_OPTION = ReserveOption.GENERAL_FIRST

# 검색 간격 (초)
SEARCH_INTERVAL = 1

# 세션 갱신 간격 (분) - 로그인 세션 유지
SESSION_REFRESH_INTERVAL = 30

# 최대 시도 횟수 (0 = 무제한)
MAX_ATTEMPTS = 0

# ============ 코드 ============


def log(message: str):
    """타임스탬프와 함께 로그 출력"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def send_telegram(message: str):
    """텔레그램으로 알림 전송"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        log(f"텔레그램 전송 실패: {e}")


def is_preferred_time(train, config: SearchConfig) -> bool:
    """원하는 시간대의 열차인지 확인"""
    if config.time_start is None or config.time_end is None:
        return True

    dep_hour = train.dep_time[:2]
    return config.time_start <= dep_hour < config.time_end


def get_seat_status(train) -> str:
    """좌석 상태 문자열 반환"""
    status = []
    if train.has_special_seat():
        status.append("특실O")
    else:
        status.append("특실X")
    if train.has_general_seat():
        status.append("일반실O")
    else:
        status.append("일반실X")
    return ", ".join(status)


def display_train_info(train) -> str:
    """열차 정보 문자열 반환"""
    seat_status = get_seat_status(train)
    return (
        f"[{train.train_type_name}] {train.dep_date[4:6]}월 {train.dep_date[6:]}일, "
        f"{train.dep_name}~{train.arr_name}"
        f"({train.dep_time[:2]}:{train.dep_time[2:4]}~{train.arr_time[:2]}:{train.arr_time[2:4]}) "
        f"[{seat_status}]"
    )


def check_seat_available(train, seat_type: SeatType) -> bool:
    """원하는 좌석 타입이 예약 가능한지 확인"""
    if seat_type == SeatType.GENERAL:
        return train.has_general_seat()
    elif seat_type == SeatType.SPECIAL:
        return train.has_special_seat()
    else:  # SeatType.ANY
        return train.has_general_seat() or train.has_special_seat()


def get_reserve_option(seat_type: SeatType) -> str:
    """좌석 타입에 맞는 ReserveOption 반환"""
    if seat_type == SeatType.GENERAL:
        return ReserveOption.GENERAL_ONLY
    elif seat_type == SeatType.SPECIAL:
        return ReserveOption.SPECIAL_ONLY
    else:  # SeatType.ANY
        return RESERVE_OPTION  # 전역 설정 사용


def search_and_reserve(korail: Korail, config: SearchConfig) -> bool:
    """열차 검색 및 예약 시도"""
    try:
        trains = korail.search_train(
            dep=config.dep_station,
            arr=config.arr_station,
            date=config.dep_date,
            time=config.dep_time,
            train_type=config.train_type,
            passengers=PASSENGERS,
            include_no_seats=True,
        )

        if not trains:
            return False

        # 원하는 시간대 열차만 필터링
        preferred_trains = [t for t in trains if is_preferred_time(t, config)]

        for train in preferred_trains:
            train_info = display_train_info(train)

            # 원하는 좌석 타입이 예약 가능한지 확인
            if check_seat_available(train, config.seat_type):
                seat_type_name = {
                    SeatType.GENERAL: "일반실",
                    SeatType.SPECIAL: "특실",
                    SeatType.ANY: "좌석",
                }[config.seat_type]
                log(f"{seat_type_name} 예약 가능! {train_info}")

                try:
                    reserve_option = get_reserve_option(config.seat_type)
                    reservation = korail.reserve(
                        train,
                        passengers=PASSENGERS,
                        option=reserve_option,
                    )

                    success_msg = f"예약 성공! ({seat_type_name})\n{reservation}"
                    log("=" * 50)
                    log(success_msg)
                    log("=" * 50)

                    # 텔레그램 알림
                    send_telegram(
                        f"<b>코레일 예약 성공! ({seat_type_name})</b>\n\n{reservation}"
                    )

                    return True

                except SoldOutError:
                    log(f"좌석 매진: {train_info}")
                except Exception as e:
                    log(f"예약 실패: {e}")
                    # 로그인 만료 시 재로그인 필요 표시
                    if "P058" in str(e) or "Need to Login" in str(e):
                        raise NeedReloginError()

    except NoResultsError:
        pass
    except NeedReloginError:
        raise  # 재로그인 필요 예외는 상위로 전파
    except Exception as e:
        log(f"검색 오류: {e}")

    return False


def main():
    """메인 함수"""
    log("=" * 50)
    log("코레일 자동 예매 (고급) 시작")

    # JSON에서 검색 설정 로드
    search_configs = load_search_configs()

    log(f"검색 설정: {len(search_configs)}개")
    for i, config in enumerate(search_configs, 1):
        seat_type_name = {
            SeatType.GENERAL: "일반실",
            SeatType.SPECIAL: "특실",
            SeatType.ANY: "전체",
        }[config.seat_type]
        log(
            f"  [{i}] {config.dep_station}->{config.arr_station} "
            f"({config.dep_date} {config.time_start or '전체'}~{config.time_end or '전체'}시) "
            f"[{seat_type_name}]"
        )
    log(f"검색 간격: {SEARCH_INTERVAL}초")
    log("=" * 50)

    # 로그인
    log("로그인 중...")
    korail = Korail(KORAIL_ID, KORAIL_PW, auto_login=True)
    if not korail.logined:
        log("로그인 실패! ID/PW를 확인해주세요.")
        return
    log("로그인 성공!")
    send_telegram("코레일 자동 예매 시작됨")

    # 자동 예매 루프
    attempt = 0
    last_refresh = datetime.now()
    reserved_configs = set()  # 이미 예약된 설정 추적

    while True:
        attempt += 1

        if MAX_ATTEMPTS > 0 and attempt > MAX_ATTEMPTS:
            log(f"최대 시도 횟수({MAX_ATTEMPTS}회) 초과. 종료합니다.")
            break

        # 모든 설정이 예약되었는지 확인
        if len(reserved_configs) >= len(search_configs):
            log("모든 설정에 대해 예약 완료!")
            break

        # 세션 갱신
        if (datetime.now() - last_refresh).seconds > SESSION_REFRESH_INTERVAL * 60:
            log("세션 갱신 중...")
            try:
                korail.login(KORAIL_ID, KORAIL_PW)
                last_refresh = datetime.now()
                log("세션 갱신 완료")
            except Exception as e:
                log(f"세션 갱신 실패: {e}")

        log(f"시도 #{attempt}")

        # 각 설정에 대해 검색 시도
        for i, config in enumerate(search_configs):
            if i in reserved_configs:
                continue

            log(f"검색: {config.dep_station}->{config.arr_station} ({config.dep_date})")

            try:
                if search_and_reserve(korail, config):
                    reserved_configs.add(i)
                    log(f"설정 [{i + 1}] 예약 완료!")
            except NeedReloginError:
                log("세션 만료 감지. 재로그인 중...")
                if korail.login(KORAIL_ID, KORAIL_PW):
                    last_refresh = datetime.now()
                    log("재로그인 성공!")
                else:
                    log("재로그인 실패! 프로그램을 종료합니다.")
                    send_telegram("재로그인 실패! 프로그램이 종료되었습니다.")
                    return
                break  # 현재 루프 중단하고 다음 시도에서 재검색

        log(f"{SEARCH_INTERVAL}초 후 재시도...")
        time.sleep(SEARCH_INTERVAL)

    log("프로그램 종료")
    log("코레일 앱 또는 홈페이지에서 결제를 완료해주세요.")


if __name__ == "__main__":
    main()
