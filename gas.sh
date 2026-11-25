#!/bin/bash
# Menu utama. Jalankan setelah git clone.
set -e
ROOT="${MTOOL_ROOT:-/srv/meowtools}"
if [ ! -f "$ROOT/menu.py" ]; then
  echo "menu.py belum terpasang. Jalankan ./install.sh dulu."
  exit 1
fi
exec /usr/bin/python3 "$ROOT/menu.py" "$@"
