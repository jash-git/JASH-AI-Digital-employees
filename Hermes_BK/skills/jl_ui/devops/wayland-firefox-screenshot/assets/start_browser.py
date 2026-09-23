#!/usr/bin/env python3
"""Daemonize a browser (Chrome/Chromium) so it survives terminal() timeout.

Double-fork detaches from the controlling terminal's process group.
Usage:
    python3 assets/start_browser.py "<URL>" [BROWSER_BIN]

Defaults to google-chrome on this GNOME+Xwayland box with correct XAUTHORITY.
"""
import os
import sys

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.google.com"
BROWSER_BIN = (
    sys.argv[2]
    if len(sys.argv) > 2
    else "/usr/bin/google-chrome"
)
DISPLAY = ":0"
XAUTHORITY = "/run/user/1000/.mutter-Xwaylandauth.MP7LV3"

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

# Daemon process: detach from terminal fds, redirect stdout/stderr to log.
sys.stdin.close()
logf = open("/tmp/browser_daemon.log", "w")
os.dup2(logf.fileno(), 1)
os.dup2(logf.fileno(), 2)

for k, v in {"DISPLAY": DISPLAY, "XAUTHORITY": XAUTHORITY}.items():
    os.environ[k] = v

# Chrome flags: --no-sandbox (needed under this sandboxed env), --disable-gpu,
# dedicated user-data-dir (avoids profile lock conflicts on headless-ish Xwayland),
# --ozone-platform=x11 (force X11 backend so the window maps to Xwayland;
# otherwise Chrome defaults to native Wayland and no X11 window appears)
os.execv(BROWSER_BIN, [BROWSER_BIN, "--no-sandbox", "--disable-gpu",
                      "--user-data-dir=/tmp/chrome-profile",
                      "--ozone-platform=x11", URL])
