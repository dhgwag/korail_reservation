#!/bin/bash
# 자동 예매 실행 (CLI)
# 사용법: ./run.sh korail   또는   ./run.sh srt   (기본: korail)

cd "$(dirname "$0")"
set -a  # 변수를 자동으로 export
source .env
set +a
source venv/bin/activate

MODE="${1:-korail}"
case "$MODE" in
  korail) python auto_reserve_korail.py ;;
  srt)    python auto_reserve_srt.py ;;
  *)      echo "알 수 없는 모드: $MODE (사용 가능: korail, srt)"; exit 1 ;;
esac
