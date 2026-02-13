#!/bin/bash
# 자동 예매 실행

cd "$(dirname "$0")"
set -a  # 변수를 자동으로 export
source .env
set +a
source venv/bin/activate
python auto_reserve_advanced.py
