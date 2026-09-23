#!/usr/bin/env bash
# check-month-select.sh — 月份選單回歸偵測器（suanming 專案專用）
#
# 用途：掃描 src/public/js，提前攔截「T-31 / 陷阱7」類缺陷——
#       日期型工具頁的 <select id="*Month"> 載入後為空（optCount=0），
#       因 JS 只有 fillDays() 填「日」、從未填充「月」，導致 calc 收 NaN。
#
# 觸發模式：
#   P1 有 fillDays() 卻沒有對應的 fillMonths()        → 月份選單永遠空
#   P2 有 Month select id（getElementById('...Month')）卻從未填充 option      → 同上
#   P3 有 fillMonth/fillDay 但整檔找不到 form.render('select')               → Layui 假下拉未同步
#
# 用法：
#   scripts/check-month-select.sh [JS_ROOT]        # 預設 JS_ROOT=src/public/js
#   exit code: 0 = 無缺陷, 1 = 發現問題
#
set -uo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/.." && pwd)/src/public/js}"
if [ ! -d "$ROOT" ]; then
  echo "❌ 找不到 JS 目錄: $ROOT" >&2
  exit 2
fi

problems=0
checked=0

# 排除測試與演算法核心（lunar.js/bazi.js 是純計算庫，不碰 select）
is_excluded() {
  case "$1" in
    */tests/*|*/algo/*) return 0 ;;
    *) return 1 ;;
  esac
}

while IFS= read -r -d '' f; do
  is_excluded "$f" && continue
  checked=$((checked+1))
  rel="${f#$ROOT/}"

  has_fill_days=$(grep -cE "function[[:space:]]+fillDays|fillDays\(" "$f")
  has_fill_months=$(grep -cE "fillMonths" "$f")
  has_month_sel=$(grep -cE "getElementById\('[^']*Month'\)" "$f")
  has_render_select=$(grep -cE "form\.render\(['"]select['"]\)" "$f")

  # P1: 有 fillDays 卻沒有 fillMonths → 月份選單永遠空
  if [ "$has_fill_days" -gt 0 ] && [ "$has_fill_months" -eq 0 ]; then
    echo "P1  ⚠️  $rel : 有 fillDays() 但無 fillMonths() —— 月份選單載入後為空（optCount=0）"
    problems=$((problems+1))
  fi

  # P2: 有 Month select id 卻從未填充 option（createElement/innerHTML/options）
  if [ "$has_month_sel" -gt 0 ] && [ "$has_fill_months" -eq 0 ]; then
    if ! grep -qE "createElement\('option'\)|\.options\[|\.innerHTML[[:space:]]*=.*option|appendOption|addMonthOptions" "$f"; then
      echo "P2  ⚠️  $rel : 有 Month select（id='...Month'）但從未填充選項 —— 需確認 load 時填 12 個 month option"
      problems=$((problems+1))
    fi
  fi

  # P3: 有 fillMonth/fillDay 卻沒有 form.render('select') → Layui 假下拉未同步
  if { [ "$has_fill_days" -gt 0 ] || [ "$has_fill_months" -gt 0 ]; } && [ "$has_render_select" -eq 0 ]; then
    echo "P3  ⚠️  $rel : 有動態 fillMonth/fillDay 但找不到 form.render('select') —— Layui 假下拉可能未同步"
    problems=$((problems+1))
  fi
done < <(find "$ROOT" -name "*.js" -type f -print0)

echo "──────────────────────────────────────"
echo "已掃描 $checked 個前端 JS 檔案（已排除 tests/、algo/）"
if [ "$problems" -eq 0 ]; then
  echo "✅ 無月份選單缺陷跡象"
  exit 0
else
  echo "❌ 發現 $problems 處潛在月份選單問題，請依 P1/P2/P3 修正後重跑"
  exit 1
fi
