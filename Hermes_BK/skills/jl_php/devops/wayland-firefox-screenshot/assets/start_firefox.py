#!/usr/bin/env python3
"""Daemonize Firefox so it survives terminal() timeout/kill.

Double-fork detaches the process from the controlling terminal's process group,
so a foreground terminal call that times out will NOT kill it.

Usage:
    python3 assets/start_firefox.py "<URL>" [DISPLAY] [XAUTHORITY] [FIREFOX_BIN]

Defaults match this box's GNOME+Xwayland+snap setup; override as needed.
"""
import os
import sys

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.google.com"
DISPLAY = sys.argv[2] if len(sys.argv) > 2 else ":0"
XAUTHORITY = (
    sys.argv[3]
    if len(sys.argv) > 3
    else "/run/user/1000/.mutter-Xwaylandauth.MP7LV3"
)
FIREFOX_BIN = (
    sys.argv[4]
    if len(sys.argv) > 4
    else "/snap/firefox/8863/usr/lib/firefox/firefox"
)

# First fork -> parent exits, child becomes session leader
pid = os.fork()
if pid > 0:
    print("First fork PID %d; daemonizing..." % pid)
    os._exit(0)
os.setsid()

# Second fork -> grandchild cannot reacquire a terminal
pid = os.fork()
if pid > 0:
    os._exit(0)

# Daemon process: detach from terminal fds, redirect stdout/stderr to a log.
sys.stdin.close()
logf = open("/tmp/firefox_daemon.log", "w")
os.dup2(logf.fileno(), 1)
os.dup2(logf.fileno(), 2)

for k, v in {
    "DISPLAY": DISPLAY,
    "XAUTHORITY": XAUTHORITY,
    "MOZ_ENABLE_WAYLAND": "0",  # force X11 backend so the window maps to Xwayland
}.items():
    os.environ[k] = v

os.execv(FIREFOX_BIN, [FIREFOX_BIN, URL])
