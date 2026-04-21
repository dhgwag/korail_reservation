#!/bin/bash
# 기차표(코레일/SRT) 자동 예매 웹 UI 실행
# 이 파일을 더블클릭하면 웹 UI가 열립니다.

cd "$(dirname "$0")"

if [ ! -d venv ]; then
    echo "venv가 없습니다. 먼저 ./setup.sh 실행이 필요합니다."
    echo "아무 키나 누르면 종료합니다..."
    read -n 1
    exit 1
fi

source venv/bin/activate
python web_ui.py
