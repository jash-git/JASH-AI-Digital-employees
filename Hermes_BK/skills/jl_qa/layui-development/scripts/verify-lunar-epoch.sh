#!/usr/bin/env bash
# verify-lunar-epoch.sh — 快速檢查 lunar.js LUNAR_INFO[0]（年 1900）閏月值是否正確
# 用法：bash scripts/verify-lunar-epoch.sh [lunar.js路徑]
# 預設路徑：src/public/js/algo/lunar.js

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

LUNAR_JS="${1:-$PROJECT_ROOT/src/public/js/algo/lunar.js}"

if [ ! -f "$LUNAR_JS" ]; then
    echo "❌ 找不到 lunar.js: $LUNAR_JS"
    exit 1
fi

echo "=== LUNAR_INFO[0]（年 1900）閏月值檢查 ==="
node -e '
var fs = require("fs");
var w = {};
global.window = w;
eval(fs.readFileSync(process.argv[2], "utf-8"));
var L = w.Lunar;

var info0 = L.info[0];
console.log("LUNAR_INFO[0] 原始值: 0x" + info0.toString(16).padStart(4, "0") + " (" + info0 + ")");
console.log("低 4 位元 (閏月): " + (info0 & 0xf));

var leap = info0 & 0xf;
if (leap === 0) {
    console.log("\u2705 1900 \u5e74\u7121\u95b0\u6708 \u2014 \u6b63\u78ba");
} else {
    console.log("\u274c 1900 \u5e74\u6709\u95b0" + ["","\u4e00","\u4e8c","\u4e09","\u56db","\u4e94","\u516d","\u4e03","\u516b","\u4e5d","\u5341","\u51ac","\u818a"][leap] + "\u6708 \u2014 \u932f\u8aa4\uff01\u61c9\u70ba 0");
}

// \u9a57\u8b49\u95dc\u9375\u65e5\u671f
console.log("\n=== \u95dc\u9375\u65e5\u671f\u9a57\u8b49 ===");
var tests = [
    {y:1981, m:1, d:27, expected:"1981/1/1 (\u8f9b\u9149\u5e74\u6b63\u6708\u521d\u4e00)"},
    {y:1980, m:2, d:16, expected:"1980/1/1 (\u5eda\u7533\u5e74\u6b63\u6708\u521d\u4e00)"},
    {y:1981, m:5, d:2,  expected:"1981/7/18"},
];

var allPass = true;
tests.forEach(function(t) {
    var r = L.solarToLunar(t.y, t.m, t.d);
    var actual = r.year + "/" + r.month + "/" + r.day;
    var pass = (r.year === parseInt(t.expected.split("/")[0]) && 
                r.month === parseInt(t.expected.split("/")[1]));
    console.log((pass ? "\u2705" : "\u274c") + " solarToLunar(" + t.y + "," + t.m + "," + t.d + ") \u2192 " + actual + " (\u9810\u671f: " + t.expected + ")");
    if (!pass) allPass = false;
});

console.log("\n" + (allPass ? "\u2705 \u5168\u90e8\u901a\u904e" : "\u274c \u6709\u5931\u6557\u9805\u76ee\uff0c\u8acb\u6aa2\u67e5 LUNAR_INFO[0]"));
process.exit(allPass ? 0 : 1);
' "$LUNAR_JS"
