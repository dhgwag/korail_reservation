#!/bin/bash
# venv 생성 및 의존성 설치

cd "$(dirname "$0")"

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# korail2 라이브러리 패치 (NoResultsError 대신 빈 리스트 반환)
KORAIL2_PATH=$(python -c "import korail2; print(korail2.__file__)")
if [ -f "$KORAIL2_PATH" ]; then
    sed -i.bak 's/raise NoResultsError()/return []  # patched/' "$KORAIL2_PATH"
    rm -f "${KORAIL2_PATH}.bak"
    echo "korail2 패치 완료!"
fi

# 더블클릭 실행 파일 권한 설정
chmod +x "$(dirname "$0")/코레일예매.command" 2>/dev/null

echo "설치 완료!"
echo "실행: 코레일예매.command 더블클릭 또는 python web_ui.py"
