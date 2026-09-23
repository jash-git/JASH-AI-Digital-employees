/* ============================================================
   xcheck.js — JS engine vs PHP oracle consistency harness
   --------------------------------------------------------
   Generic version of the suanming bazi-core-xcheck.js.
   Loads a browser/UMD JS engine in-process via vm sandbox,
   shells out to a pure-function PHP oracle on stdin, and
   compares results field-by-field for each input case.

   Adapt: ALGO paths, CASES array, comparison fields (eq/wEq).

   Usage: node scripts/xcheck.js
   ============================================================ */
'use strict';
const fs = require('fs');
const vm = require('vm');
const { execFileSync } = require('child_process');

// ---- Paths (adapt per project) ----
const ROOT = __dirname;                       // .../scripts
const ALGO = process.env.ALGO || ROOT + '/../src/public/js/algo';
const PHP_ORACLE = process.env.PHP_ORACLE || ROOT + '/../src/public/js/tests/php-oracle.php';

// ---- Load browser/UMD JS engine in a VM sandbox ----
// Browser JS guards on window/define/module.exports and may assign to global.X.
// Set both so the module lands on our sandbox instead of throwing silently.
const sandbox = {};
sandbox.window = sandbox;                     // e.g. lunar.js compat layer sets window.Solar
sandbox.global = sandbox;                     // e.g. bazi.js does `global.Bazi = Bazi`
vm.createContext(sandbox);

function run(src, name) {
  vm.runInContext(src, sandbox, { filename: name });
}

// ---- Load engine A (JS) ----
run(fs.readFileSync(ALGO + '/lunar.js', 'utf8'), 'lunar.js');
if (typeof sandbox.window.Solar !== 'function' && typeof sandbox.window.Solar !== 'object') {
  console.error('✗ lunar.js UMD else branch did not run (window.Solar missing)');
  process.exit(1);
}
run(fs.readFileSync(ALGO + '/bazi.js', 'utf8'), 'bazi.js');
// NOTE: expose name may differ — check the source's trailing `global.X = X`.
const B = sandbox.window.Bizi || sandbox.window.Bazi;
if (!B || typeof B.calc !== 'function') {
  console.error('✗ bazi.js did not expose window.Bizi/Bizi.calc');
  process.exit(1);
}

// ---- Test cases: [year, month, day, hour] (add boundaries) ----
const CASES = [
  [1981, 5, 2, 12],
  [1984, 2, 2, 0],
  [1990, 8, 15, 13],
  [2000, 1, 6, 7],
  [1978, 12, 31, 23],
  [1995, 2, 4, 1],
  [1966, 10, 1, 18],
];

// ---- Comparison helpers (adapt per domain) ----
function eq(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function wxEq(x, y) {
  for (const k of ['金', '木', '水', '火', '土']) {
    if (Math.abs((x[k] || 0) - (y[k] || 0)) > 0.01) return false;
  }
  return true;
}

// ---- Run both engines, compare field-by-field ----
let pass = 0, fail = 0; const fails = [];

for (const [y, m, d, h] of CASES) {
  // Engine A (JS)
  const res = B.calc(y, m, d, h, 1);
  const jsPillars = res.pillars.map(p => [p.gan, p.zhi]);
  const jsSheng = res.shengxiao;
  const jsWx = res.wuxing;

  // Engine B (PHP oracle via child_process)
  let phpRes;
  try {
    const input = JSON.stringify([{ y, m, d, h }]) + '\n';
    phpRes = JSON.parse(execFileSync('php', [PHP_ORACLE], { input: input, encoding: 'utf8' }))[0];
  } catch (e) {
    console.error(`✗ ${y}/${m}/${d} h=${h}: PHP oracle failed (${e.message})`);
    fail++; continue;
  }

  const errs = [];
  if (!eq(jsPillars, phpRes.pillars)) errs.push('pillars');
  if (!wxEq(jsWx, phpRes.wx)) errs.push('wx');
  // Convention differences (e.g. shengxiao year convention) are flagged, not auto-failed:
  if (jsSheng !== phpRes.shengxiao) errs.push(`shengXiao:${jsSheng}(JS) vs ${phpRes.shengxiao}(PHP)`);

  const ok = errs.length === 0;
  if (ok) pass++; else { fail++; fails.push({ case: [y, m, d, h], errs }); }

  console.log(`${y}/${m}/${d} h=${h}: ${ok ? 'PASS' : 'FAIL'} | pillars=` +
    jsPillars.join('|') + ` sheng=${jsSheng} wx金=${jsWx['金']}`);
}

console.log(`\n=== JS vs PHP oracle consistency: PASS=${pass} FAIL=${fail} ===`);
for (const f of fails) console.log('  ✗', JSON.stringify(f));
process.exit(fail > 0 ? 1 : 0);
