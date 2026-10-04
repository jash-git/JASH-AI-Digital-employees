#!/bin/bash
# 隔天當沖選股 — 每日執行包裝（收盤後使用）
# 用法：bash run.sh            # 預設 top12 / min-score45
#      bash run.sh --top 8    # 自訂
set -e
cd "$(dirname "$0")"
OUT="results/scan_$(date +%Y%m%d).csv"
mkdir -p results
python3 scanner.py "$@" --out-csv "$OUT"
echo ""
echo ">>> CSV 已存至：$PWD/$OUT"
