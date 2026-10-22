---
name: comfyui-troubleshooting
category: devops
description: When ComfyUI won't start, find the crashing native ext.
---

# ComfyUI Troubleshooting

Use when ComfyUI fails to start, exits during startup, shows no web server, or a custom node will not load — particularly when the failure looks like a crash with no clear Python error.

## Always-on rules

- Treat a "silent" startup exit as a native segfault until proven otherwise. If the process returns to the shell prompt (a batch `pause` runs) without printing `[Prompt Server] listening on http://...` and without any Python `Traceback`, a C-level crash took down the interpreter. A pure-Python exception always prints a traceback; a C extension crash does not.
- Confirm the server never bound before debugging code. Probe the HTTP port (TCP connect to 127.0.0.1 or the remote host :8188). Connection refused = nothing is serving; this separates "crashed at startup" from "running but unreachable" and avoids chasing code that is actually fine.
- Verify against the exact access pattern the production loader uses. A bare `import package` passing does NOT prove `from package import Class` or `Class()` instantiation works — module init, class attribute resolution, and constructor each run different code. Reproduce what the node's top-level import chain actually executes before declaring a build OK.
- Test every native dependency of the failing node in load order; do not tunnel-vision on the component you most recently rebuilt. A pre-installed wheel (e.g. pynanoinstantmeshes) can segfault at import while the freshly built one passes a bare import. The thing you just changed is the least likely to be innocent — verify the whole top-level import chain of the node.
- For torch C++ extensions, build against the same compiler family the installed torch was compiled with. ROCm/AMD PyTorch is built with AMD's clang (amdclang-cl); an extension built with plain clang-cl or MSVC cl can produce symbol/ABI mismatches that surface as a silent import segfault rather than a clean ImportError. Mismatched compiler families are the usual cause of "built OK but crashes on import." Match the family, then re-verify with class access + instantiation.

## Procedure

1. Capture a full startup log to a file inside the install dir (redirect stdout+stderr); console scrollback truncates and `ComfyUI/logs/` may not exist if it crashes early.
2. Read the tail: confirm whether `[Prompt Server] listening` / `Thank you for using ComfyUI` appear. If absent, startup died during custom-node loading — move to step 3.
3. Build an isolated import probe that imports each native dep of the failing node in load order and prints a marker after each (see templates/import-probe.py). Whichever marker is last before the process dies silently, or the first `[ERR]`, is the culprit. A segfault kills the whole process with no output past it.
4. Isolate the fix to the identified component only: rebuild it with the matching compiler family (references/native-extension-import-failures.md), or reinstall/swap its version if it is a pre-installed wheel. Do not keep rebuilding the same package while the real culprit is an untouched one.
5. Back up any `.pyd` / installed package you are about to overwrite before rebuilding, so a bad rebuild is reversible in one copy.

## Support files

- `templates/import-probe.py` — copy-ready isolated import probe; run it on the machine that has the real torch to pinpoint which native dep crashes.
- `references/native-extension-import-failures.md` — compiler-family matching table, load-order testing rationale, and the verify-matches-loader checklist.
