#!/bin/bash
set -e
BASE=${GOOGLE_PRO_DIR:-/srv/meowtools/google-pro}
export ADB_PATH="$BASE/adb-waydroid"
export PYTHONIOENCODING=utf-8
export FRIDA_ARCH=x86_64
export PATH="/usr/bin:$PATH"
cd "$BASE"
/usr/bin/python3 ultra0.py "$@"
