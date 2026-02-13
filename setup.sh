#!/bin/bash
# venv 생성 및 의존성 설치

cd "$(dirname "$0")"

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "설치 완료!"
