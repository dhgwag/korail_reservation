#!/bin/bash
# 기차표 자동 예매: venv 생성 + 의존성 설치 + korail2 패치
set -e

cd "$(dirname "$0")"

# venv
if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 의존성 (코레일/SRT 라이브러리 fork 포함)
pip install -r requirements.txt

# korail2 라이브러리 패치 (NoResultsError 대신 빈 리스트 반환)
KORAIL2_PATH=$(python -c "import korail2; print(korail2.__file__)")
if [ -f "$KORAIL2_PATH" ]; then
    sed -i.bak 's/raise NoResultsError()/return []  # patched/' "$KORAIL2_PATH"
    rm -f "${KORAIL2_PATH}.bak"
    echo "korail2 패치 완료"
fi

# .env 자동 생성 (처음 설치 시)
if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo ".env 생성됨 (.env.example 복제) — 로그인 정보 입력 필요"
fi

# 실행 권한
chmod +x 기차표예매.command run.sh 2>/dev/null || true

echo ""
echo "설치 완료!"
echo "실행: 기차표예매.command 더블클릭  또는  python web_ui.py"
echo "CLI: ./run.sh korail  또는  ./run.sh srt"
