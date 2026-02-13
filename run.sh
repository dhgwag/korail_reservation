#!/bin/bash
# 자동 예매 실행

cd "$(dirname "$0")"
source venv/bin/activate
python auto_reserve_advanced.py
