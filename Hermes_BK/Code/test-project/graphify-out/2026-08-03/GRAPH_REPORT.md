# Graph Report - .  (2026-08-03)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 59 nodes · 93 edges · 15 communities (12 shown, 3 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- H
- b
- t
- wt
- A
- Et
- i
- q

## God Nodes (most connected - your core abstractions)
1. `t()` - 8 edges
2. `H()` - 8 edges
3. `ye()` - 7 edges
4. `s()` - 7 edges
5. `p()` - 5 edges
6. `y()` - 5 edges
7. `ne()` - 5 edges
8. `b()` - 5 edges
9. `w()` - 4 edges
10. `q()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `y()` --indirect_call--> `t()`  [INFERRED]
  src/public/lib/layui/layui.js → src/public/lib/layui/layui.js  _Bridges community 1 → community 3_
- `H()` --indirect_call--> `i()`  [INFERRED]
  src/public/lib/layui/layui.js → src/public/lib/layui/layui.js  _Bridges community 1 → community 8_
- `s()` --indirect_call--> `b()`  [INFERRED]
  src/public/lib/layui/layui.js → src/public/lib/layui/layui.js  _Bridges community 2 → community 1_
- `Et()` --calls--> `p()`  [EXTRACTED]
  src/public/lib/layui/layui.js → src/public/lib/layui/layui.js  _Bridges community 1 → community 7_
- `ye()` --calls--> `q()`  [EXTRACTED]
  src/public/lib/layui/layui.js → src/public/lib/layui/layui.js  _Bridges community 9 → community 1_

## Import Cycles
- None detected.

## Communities (15 total, 3 thin omitted)

### Community 1 - "H"
Cohesion: 0.33
Nodes (9): de(), H(), he(), me(), p(), s(), tn(), y() (+1 more)

### Community 2 - "b"
Cohesion: 0.29
Nodes (8): b(), be(), Ee(), Je(), ne(), Ve(), w(), we()

### Community 3 - "t"
Cohesion: 0.29
Nodes (7): fe(), ge(), K(), le(), Qt(), t(), ue()

### Community 4 - "wt"
Cohesion: 0.50
Nodes (4): pe(), Qe(), wt(), Ze()

### Community 5 - "A"
Cohesion: 0.67
Nodes (3): A(), At(), jt()

## Knowledge Gaps
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `t()` connect `t` to `layui.js`, `H`?**
  _High betweenness centrality (0.006) - this node is a cross-community bridge._
- **Why does `H()` connect `H` to `layui.js`, `i`, `b`, `t`?**
  _High betweenness centrality (0.005) - this node is a cross-community bridge._
- **Why does `s()` connect `H` to `layui.js`, `b`?**
  _High betweenness centrality (0.004) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `t()` (e.g. with `fe()` and `ge()`) actually correct?**
  _`t()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `H()` (e.g. with `i()` and `s()`) actually correct?**
  _`H()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `ye()` (e.g. with `p()` and `s()`) actually correct?**
  _`ye()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `s()` (e.g. with `H()` and `b()`) actually correct?**
  _`s()` has 4 INFERRED edges - model-reasoned connections that need verification._