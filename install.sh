#!/bin/bash
# One-command installer for the sanitized Waydroid toolkit.
# Usage: git clone <repo> && cd <repo> && sudo ./install.sh
set -euo pipefail

if [ "$(id -u)" != "0" ]; then
  echo "Jalankan sebagai root: sudo ./install.sh"
  exit 1
fi

ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
  echo "Toolkit ini untuk x86_64. Arsitektur terdeteksi: $ARCH"
  exit 1
fi

SRC="$(cd "$(dirname "$0")" && pwd)"
ROOT="${MTOOL_ROOT:-/srv/meowtools}"
GP="$ROOT/google-pro"
CV="$ROOT/credvault"
WR="$ROOT/waydroid-web"
Q="$ROOT/gemini_queue"
TD="$ROOT/templates"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
ENABLE_SERVICES="${ENABLE_SERVICES:-1}"
SKIP_APT="${SKIP_APT:-0}"
SKIP_INIT="${SKIP_INIT:-0}"
DOMAIN="${DOMAIN:-}"
TAILSCALE_IP="${TAILSCALE_IP:-}"
BASE_PATH="${BASE_PATH:-/geminitoddd2tahun}"
BIND_HOST="${TAILSCALE_IP:-127.0.0.1}"

svc() {
  if [ "$ENABLE_SERVICES" = "1" ]; then
    "$@"
  fi
}

echo "[1/9] Install dependency dasar"
if [ "$SKIP_APT" = "0" ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq curl ca-certificates gnupg git unzip python3 python3-pip \
    python3-flask android-tools-adb socat xz-utils xvfb || {
    echo "Gagal install paket dasar."
    exit 1
  }

  echo "[2/9] Pastikan repo Waydroid terdaftar"
  if ! grep -Rqs 'repo.waydro.id' /etc/apt/sources.list.d/; then
    CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
    curl -fsSL --max-time 30 https://repo.waydro.id/waydroid.gpg -o /tmp/waydroid.gpg
    install -m 644 /tmp/waydroid.gpg /usr/share/keyrings/waydroid.gpg
    echo "deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydro.id/ $CODENAME main" \
      > /etc/apt/sources.list.d/waydroid.list
    apt-get update -qq
    apt-get install -y -qq waydroid lxc weston
  fi
else
  echo "SKIP_APT=1, lewati apt."
fi

echo "[3/9] Python packages"
"$PYTHON_BIN" -m pip install -q --break-system-packages \
  'frida==16.5.9' cryptography pillow flask bcrypt

echo "[4/9] Siapkan folder dan file"
mkdir -p "$GP" "$CV" "$WR" "$Q" "$TD"
cp -a "$SRC/google-pro/." "$GP/"
cp -a "$SRC/menu.py" "$ROOT/menu.py"
cp -a "$SRC/gas.sh" "$ROOT/gas.sh"
chmod +x "$ROOT/gas.sh"
cp -a "$SRC/credvault/." "$CV/"
cp -a "$SRC/app_remote.py" "$WR/app_remote.py"
cp -a "$SRC/queue_app.py" "$Q/app.py"
cp -a "$SRC/templates/." "$TD/"
chmod 700 "$CV" "$GP" "$WR" "$Q" "$TD"
find "$GP" "$CV" "$WR" "$Q" -type f -name '*.sh' -exec chmod +x {} +

echo "[5/9] Kunci lokal"
if [ ! -f "$CV/key.bin" ]; then
  "$PYTHON_BIN" -c 'import os; open("'"$CV"'/key.bin","wb").write(os.urandom(32))'
  chmod 600 "$CV/key.bin"
fi
if [ ! -f "$Q/secret.key" ]; then
  "$PYTHON_BIN" -c 'import os; open("'"$Q"'/secret.key","wb").write(os.urandom(32))'
  chmod 600 "$Q/secret.key"
fi
if [ ! -f "$WR/password.txt" ]; then
  "$PYTHON_BIN" - "$WR" <<'PY'
import secrets, sys, bcrypt
from pathlib import Path
base = Path(sys.argv[1])
pw = secrets.token_urlsafe(12)
h = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
(base / "password.txt").write_text(pw + "\n")
(base / "hash.txt").write_text(h + "\n")
(base / "password.txt").chmod(0o600)
(base / "hash.txt").chmod(0o600)
PY
  echo "Password remote dibuat di $WR/password.txt (0600)."
fi

echo "[6/9] Frida server x86_64"
if [ ! -f "$GP/frida-server-x86_64" ]; then
  if [ -n "${FRIDA_SERVER_SRC:-}" ] && [ -f "$FRIDA_SERVER_SRC" ]; then
    cp "$FRIDA_SERVER_SRC" "$GP/frida-server-x86_64"
  else
    curl -fsSL --max-time 120 \
      -o "$GP/frida-server.xz" \
      https://github.com/frida/frida/releases/download/16.5.9/frida-server-16.5.9-android-x86_64.xz
    xz -dkf "$GP/frida-server.xz"
    mv -f "$GP/frida-server" "$GP/frida-server-x86_64" 2>/dev/null || true
  fi
  chmod 755 "$GP/frida-server-x86_64"
  mkdir -p /root/.hermes/cache/scratch
  cp "$GP/frida-server-x86_64" /root/.hermes/cache/scratch/frida-server-x86_64
  chmod 755 /root/.hermes/cache/scratch/frida-server-x86_64
fi

echo "[7/9] Systemd units"
modprobe binder_linux 2>/dev/null || true
mkdir -p /dev/binderfs "$SYSTEMD_DIR/waydroid-container.service.d"
cp "$TD/dev-binderfs.mount" "$SYSTEMD_DIR/dev-binderfs.mount"
cp "$TD/waydroid-container-override.conf" \
  "$SYSTEMD_DIR/waydroid-container.service.d/override.conf"

if [ -n "$TAILSCALE_IP" ]; then
  sed "s/__TAILSCALE_IP__/$TAILSCALE_IP/g" "$TD/waydroid-adb-relay.service" \
    > "$SYSTEMD_DIR/waydroid-adb-relay.service"
fi

sed "s#__ROOT__#$ROOT#g" "$TD/waydroid-remote.service" \
  > "$SYSTEMD_DIR/waydroid-remote.service"

sed -e "s#__ROOT__#$ROOT#g" \
    -e "s#__BIND_HOST__#$BIND_HOST#g" \
    "$TD/gemini-queue.service" > "$SYSTEMD_DIR/gemini-queue.service"

svc systemctl daemon-reload
svc systemctl enable --now dev-binderfs.mount
svc systemctl enable --now waydroid-remote.service
svc systemctl enable --now gemini-queue.service
if [ -n "$TAILSCALE_IP" ]; then
  svc systemctl enable --now waydroid-adb-relay.service
fi

echo "[8/9] Caddy / akses web"
if [ -n "$DOMAIN" ]; then
  HASH=$(cat "$WR/hash.txt")
  "$PYTHON_BIN" - "$WR/Caddyfile.generated" "$DOMAIN" "$HASH" <<'PY'
import sys
from pathlib import Path
out, domain, hashed = Path(sys.argv[1]), sys.argv[2], sys.argv[3].strip()
cfg = f'''{domain} {{
    encode gzip

    handle /waydroid/* {{
        basicauth {{
            wd {hashed}
        }}
        reverse_proxy 127.0.0.1:8765
    }}

    handle /geminitoddd2tahun {{
        redir * /geminitoddd2tahun/ 302
    }}

    handle_path /geminitoddd2tahun/* {{
        reverse_proxy 127.0.0.1:8766
    }}

    handle {{
        root * /var/www/meow
        file_server
        try_files {{path}}/index.html {{path}}.html {{path}} =404
    }}
}}
'''
out.write_text(cfg)
out.chmod(0o600)
PY
  if [ ! -f /etc/caddy/Caddyfile ]; then
    mkdir -p /etc/caddy
    cp "$WR/Caddyfile.generated" /etc/caddy/Caddyfile
    echo "Caddyfile dibuat dari DOMAIN=$DOMAIN."
    svc systemctl enable --now caddy
  else
    echo "Caddyfile sudah ada. Template ada di $WR/Caddyfile.generated, merger manual."
  fi
else
  echo "DOMAIN kosong. Panel bisa diakses lewat Tailscale/SSH tunnel."
  if [ -n "$TAILSCALE_IP" ]; then
    echo "Antrean: http://$TAILSCALE_IP:8766$BASE_PATH/"
  else
    echo "Antrean: http://127.0.0.1:8766$BASE_PATH/"
  fi
fi

echo "[9/9] Waydroid image"
if [ "$SKIP_INIT" = "0" ] && [ ! -f /var/lib/waydroid/images/system.img ]; then
  echo "Mengunduh image Waydroid GAPPS. Ini bisa memakan waktu."
  waydroid init -f -s GAPPS
fi

echo "[9.5/9] Runtime preflight"
for f in /var/lib/waydroid/waydroid.prop /var/lib/waydroid/waydroid_base.prop; do
  [ -f "$f" ] && sed -i 's/^ro\.adb\.secure=1/ro.adb.secure=0/' "$f"
done
mkdir -p /run/user/0/pulse && touch /run/user/0/pulse/native && chmod 666 /run/user/0/pulse/native
if ! pgrep -f "Xvfb :100" >/dev/null; then
  nohup Xvfb :100 -screen 0 1280x800x24 +extension RANDR +render -noreset \
    >/var/log/xvfb-waydroid.log 2>&1 &
  sleep 2
fi

echo
echo "INSTALL SELESAI"
echo "Langkah berikutnya:"
echo "1. Tambah kredensial: $CV/vault add akun1"
echo "2. Start runtime: $GP/start-runtime.sh"
echo "3. Cek: $GP/0_cek.sh"
echo "4. Login Google di Waydroid, lalu submit job di panel antrean."
echo
echo "Jangan pernah commit key.bin, secret.key, vault.enc, password.txt, hash.txt, token, atau report."
