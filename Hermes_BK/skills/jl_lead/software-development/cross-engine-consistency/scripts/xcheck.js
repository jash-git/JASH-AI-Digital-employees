#!/usr/bin/env node
/* ============================================================
   xcheck.js — Cross-Engine Consistency Harness (generic starter)
   --------------------------------------------------------
   Loads a browser/UMD JS engine in-process via vm.createContext,
   runs a second engine (e.g. PHP oracle) as a child process on
   stdin, and compares results field-by-field across a spread of
   inputs.

   ADAPT THESE THREE THINGS for your project:
     - ENGINE_FILES : the JS module(s) to load into the sandbox
     - ORACLE_CMD   : [command, ...args] that reads JSON inputs on
                      stdin and writes structured results on stdout
     - CASES        : input objects shared by both engines
     - compare()    : how to normalize + diff one result pair

   Usage:  node scripts/xcheck.js
   Exit:   0 if all cases agree, 1 otherwise.
   ============================================================ */
'use strict';
const fs = require('fs');
const vm = require('vm');
const { execFileSync } = require('child_process');

// ---- CONFIG (adapt per project) ----
const ENGINE_FILES = [
  // path to each JS module, in load order. Must expose its API on window.
  'src/public/js/algo/lunar.js',
  'src/public/js/algo/bazi.js',
];
const ORACLE_CMD = ['php', 'src/public/js/tests/php-oracle.php'];
const CASES = [
  // {y:1981,m:5,d:2,h:12} — spread across boundaries, not just happy path
  { y: 1981, m: 5, d: 2, h: 12 },
  { y: 1984, m: 2, d: 2, h: 0 },
  { y: 1990, m: 8, d: 15, h: 13 },
];

// ---- Load JS engine into a browser-style sandbox ----
const sandbox = {};
sandbox.window = sandbox;   // UMD compat layer sets window.Solar etc.
sandbox.global = sandbox;   // module may assign global.X (Node-only) — land on sandbox
vm.createContext(sandbox);
for (const f of ENGINE_FILES) {
  vm.runInContext(fs.readFileSync(f, 'utf8'), sandbox, { filename: f });
}
// Resolve the engine's calc entry point after load.
const B = sandbox.window.Bizi || sandbox.window.Bazi;
if (!B || typeof B.calc !== 'function') {
  console.error('✗ JS engine did not expose a .calc() function on window');
  process.exit(1);
}

// ---- Compare two result pairs (ADAPT THIS) ----
function eq(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function wxEq(x, y) {
  for (const k of ['金', '木', '水', '火', '土']) {
    if (Math.abs((x[k] || 0) - (y[k] || 0)) > 0.01) return false;
  }
  return true;
}
function compare(jsRes, phpRes) {
  // Return list of diverging field labels (empty = agree).
  const errs = [];
  if (!eq(jsRes.pillars, phpRes.pillars)) errs.push('pillars');
  if (!wxEq(jsRes.wuxing, phpRes.wx)) errs.push('wx');
  // Classify each divergence: algorithm-mismatch vs intended-convention.
  if (jsRes.shengxiao !== phpRes.shengxiao) {
    errs.push(`shengXiao:${jsRes.shengxiao}(JS) vs ${phpRes.shengxiao}(PHP)`);
  }
  return errs;
}

// ---- Run both engines on each case, compare ----
let pass = 0, fail = 0; const fails = [];
for (const c of CASES) {
  const jsRes = B.calc(c.y, c.m, c.d, c.h, 1);
  let phpRes;
  try {
    const out = execFileSync(ORACLE_CMD[0], ORACLE_CMD.slice(1),
      { input: JSON.stringify([c]) + '\n', encoding: 'utf8' });
    phpRes = JSON.parse(out)[0];
  } catch (e) {
    console.error(`✗ oracle failed for ${JSON.stringify(c)} (${e.message})`);
    fail++; continue;
  }
  const errs = compare(jsRes, phpRes);
  if (errs.length === 0) pass++;
  else { fail++; fails.push({ case: c, errs }); }
  console.log(`${JSON.stringify(c)}: ${errs.length ? 'FAIL' : 'PASS'} | ` +
    (errs.length ? errs.join(', ') : 'all fields agree'));
}
console.log(`\n=== Cross-engine consistency: PASS=${pass} FAIL=${fail} ===`);
for (const f of fails) console.log('  ✗', JSON.stringify(f));
process.exit(fail > 0 ? 1 : 0);
