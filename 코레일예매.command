#!/bin/bash
# 코레일 자동 예매 웹 UI 실행
# 이 파일을 더블클릭하면 웹 UI가 열립니다.

cd "$(dirname "$0")"
source venv/bin/activate
python web_ui.py
