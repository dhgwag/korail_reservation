#!/bin/bash
# 기차표 자동 예매 CLI 실행
# 사용법: ./run.sh korail   또는   ./run.sh srt   (기본: korail)
set -e

cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo ".env 파일이 없습니다. 먼저 ./setup.sh 실행 후 .env를 편집하세요."
    exit 1
fi

set -a  # 자동 export
source .env
set +a
source venv/bin/activate

MODE="${1:-korail}"
case "$MODE" in
  korail) exec python auto_reserve_korail.py ;;
  srt)    exec python auto_reserve_srt.py ;;
  *)
    echo "알 수 없는 모드: $MODE"
    echo "사용법: ./run.sh [korail|srt]"
    exit 1
    ;;
esac
