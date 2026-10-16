---
name: terminal-long-download
description: "terminal 長任務超時被 kill：double-fork daemonize 跨 poll 存活"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [terminal, long-running, download, daemonize, background, timeout]
    category: devops
---

# Long-Running Terminal Tasks (Daemonize)

## When to Use This
Use when a `terminal()` foreground call would time out (~420s hard cap) or get killed mid-flight while doing something long — large downloads, batch HLS/stream segment fetching, long compute. The foreground process-group is killed on timeout, so the job dies with it.

## The Problem
`terminal()` foreground calls kill the whole process group when they hit the timeout (default 180s, hard ~420s). A big download started inside will be terminated along with the call — you lose partial progress and must restart.

## Fix: Double-Fork Daemonize (survives separate polls)
Daemonize in Python before/inside the command so the child detaches from the process group and keeps running after the foreground call returns. Then poll the log file across separate `terminal()` calls.

```python
import os, sys
log = open("/path/to/download.log", "a")
pid = os.fork()
if pid > 0:
    os._exit(0)          # parent returns immediately
os.setsid()              # detach from controlling terminal
pid2 = os.fork()
if pid2 > 0:
    os._exit(0)          # grandparent returns
# now in grandchild: redirect std fds to log, run the long job
sys.stdout.flush(); sys.stderr.flush()
os.dup2(log.fileno(), 1); os.dup2(log.fileno(), 2)
# <run your download here>
```

Then from later `terminal()` calls just tail the log / check the output file. Verified working for a missav HLS segment download — survived multiple separate terminal polls without dying.

## Simpler Alternative: background=true
`terminal(background=True)` tracks the process itself and returns a session_id; poll it with process_manage instead of daemonizing manually. Prefer this when you just need to run-and-monitor rather than fully detach.

## Gotchas
- Daemonized children keep running after the session ends unless they finish or are killed — clean up (pkill / kill pid) when done, or they'll linger.
- Write progress to a log file + pid file so later calls can find and monitor it.
- Don't rely on variables/state across `terminal()` calls — each is a fresh interpreter; persist state to disk.
