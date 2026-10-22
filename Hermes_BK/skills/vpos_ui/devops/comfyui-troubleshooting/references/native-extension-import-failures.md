# Native C++ extension import failures in ComfyUI

Depth for when a custom node dies at startup with no Python traceback (a segfault)
or a clean ImportError from a torch C++ extension. The SKILL.md procedure gets you
to the culprit; this file holds the technique needed to fix it.

## Why "built OK" still crashes on import

`pip install .` succeeding only means the wheel compiled and linked. It does not
mean the resulting `.pyd` will load under the *installed* torch, because loading
executes module-init code that resolves `at::` / `c10::` symbols against
`torch_cpu.dll`. If the extension was built with a different compiler family or ABI
than the installed torch, those symbols resolve wrong (or not at all) and the
crash shows up as a silent segfault at import rather than an ImportError. A bare
`import pkg` in a verify step can pass while `from pkg import Class` / instantiation
hits the bad code path.

## Compiler-family matching table

Build the extension with the same compiler family the target torch was built with:

| Installed torch                     | Build extension with        |
|-------------------------------------|-----------------------------|
| AMD / ROCm PyTorch (e.g. +rocm7.x)  | AMD clang: `amdclang-cl.exe` |
| NVIDIA CUDA PyTorch                 | MSVC cl.exe (default)       |
| CPU-only PyTorch                    | MSVC cl.exe or system gcc   |

For ROCm on Windows, locate `amdclang-cl.exe` inside the embedded python's rocm SDK
(`...\python_embeded\Lib\site-packages\_rocm_sdk_core\lib\llvm\bin\`). Set both CC and
CXX to it; torch's `CppExtension`/`BuildExtension` then emits link flags in the family
the installed torch expects. On Windows you still need the Windows SDK 10 headers/libs
(INC/LIB) on the environment for clang-cl to resolve system symbols.

## Load-order testing rationale

A node's top-level imports run in source order and each can segfault independently.
Test them in that same order with a marker after each; the last marker before the
process dies silently, or the first `[ERR]`, is the culprit. Do not assume the failure
is the package you most recently rebuilt -- a pre-installed wheel imported earlier in
the chain is often the real cause and passing its bare import gives false confidence.

## Verify-matches-loader checklist

Before declaring a rebuild successful, confirm it passes the *exact* access the node
does at startup, not just a bare import:

- [ ] `import <pkg>` loads (module init runs clean)
- [ ] `from <pkg> import <Class>` resolves the attribute the node reads
- [ ] `<Class>()` instantiates if the node constructs it at load time
- [ ] The full custom-node package imports under the real torch (run the node's own
      top-level module, or an isolated probe of its whole import chain)

If any of these crash silently where the previous one printed OK, that step is the
failure point -- fix that component specifically rather than rebuilding everything.
