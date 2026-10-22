# Copy to the ComfyUI install root and run with ITS embedded python:
#   .\python_embeded\python.exe -s import-probe.py
#
# A segfault kills the whole process with no output past it, so the LAST line
# printed (or the first [ERR]) identifies which native dependency crashes at
# import -- exactly what a custom node's top-level import chain hits on startup.
import sys


def try_import(name):
    try:
        __import__(name)
        print(f"[OK]   {name}", flush=True)
        return True
    except SystemExit:
        raise
    except Exception as e:  # ImportError / ModuleNotFoundError / DLL load failure
        print(f"[ERR]  {name} -> {type(e).__name__}: {e}", flush=True)
        return False


def try_class(name, attr):
    try:
        mod = __import__(name)
        getattr(mod, attr)
        print(f"[OK]   {name}.{attr} (access)", flush=True)
        return True
    except SystemExit:
        raise
    except Exception as e:
        print(f"[ERR]  {name}.{attr} -> {type(e).__name__}: {e}", flush=True)
        return False


# 1) plain imports first, in the order a node's module-load chain hits them
for m in ["torch", "numpy", "gpytoolbox", "pynanoinstantmeshes", "trimesh"]:
    if not try_import(m):
        sys.exit(0)

# 2) native ext that the node hard-requires at import: class access + instantiate
if try_class("uv_unwrapper", "Unwrapper"):
    try:
        getattr(__import__("uv_unwrapper"), "Unwrapper")()
        print("[OK]   uv_unwrapper (Unwrapper()) instantiate", flush=True)
    except Exception as e:
        print(f"[ERR]  uv_unwrapper (instantiate) -> {type(e).__name__}: {e}", flush=True)

print("ALL_DONE", flush=True)
