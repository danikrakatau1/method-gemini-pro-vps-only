#!/bin/bash
# 1 - Lihat daftar offer (aman, tidak membeli)
set -e
BASE=${GOOGLE_PRO_DIR:-/srv/meowtools/google-pro}
export ADB_PATH="$BASE/adb-waydroid"
export PYTHONIOENCODING=utf-8
export FRIDA_ARCH=x86_64
cd "$BASE"
/usr/bin/python3 ultra0.py --list --force
