#!/bin/bash
# 3 - Pro +6 bulan langkah 2 (total 18 bulan)
set -e
BASE=${GOOGLE_PRO_DIR:-/srv/meowtools/google-pro}
export ADB_PATH="$BASE/adb-waydroid"
export PYTHONIOENCODING=utf-8
export FRIDA_ARCH=x86_64
cd "$BASE"
/usr/bin/python3 ultra0.py --account "current@device" --no-add --force --stack --plan pro6 "$@"
