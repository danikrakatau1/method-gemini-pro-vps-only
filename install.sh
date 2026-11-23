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

echo "[1/8] Install dependency dasar"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl ca-certificates gnupg git unzip python3 python3-pip \
  python3-flask android-tools-adb socat xz-utils || {
  echo "Gagal install paket dasar."
  exit 1
}

echo "[2/8] Pastikan repo Waydroid terdaftar"
if ! grep -Rqs 'repo.waydro.id' /etc/apt/sources.list.d/; then
  CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
  curl -fsSL --max-time 30 https://repo.waydro.id/waydroid.gpg -o /tmp/waydroid.gpg
  install -m 644 /tmp/waydroid.gpg /usr/share/keyrings/waydroid.gpg
  echo "deb [signed-by=/usr/share/keyrings/waydroid.gpg] https://repo.waydro.id/ $CODENAME main" \
    > /etc/apt/sources.list.d/waydroid.list
  apt-get update -qq
  apt-get install -y -qq waydroid lxc weston
fi

echo "[3/8] Python packages"
python3 -m pip install -q --break-system-packages 'frida==16.5.9' cryptography pillow flask

echo "[4/8] Siapkan folder dan file"
mkdir -p "$GP" "$CV" "$WR"
cp -a "$SRC/google-pro/." "$GP/"
cp -a "$SRC/credvault/." "$CV/"
cp -a "$SRC/app_remote.py" "$WR/app_remote.py"
cp -a "$SRC/templates/." "$ROOT/templates/" 2>/dev/null || true
chmod 700 "$CV" "$GP" "$WR"
chmod 600 "$CV/key.bin" 2>/dev/null || true
find "$GP" "$CV" "$WR" -type f -name '*.sh' -exec chmod +x {} +

echo "[5/8] Kunci vault lokal"
if [ ! -f "$CV/key.bin" ]; then
  python3 -c 'import os; open("'"$CV"'/key.bin","wb").write(os.urandom(32))'
  chmod 600 "$CV/key.bin"
  echo "Kunci vault dibuat: $CV/key.bin"
fi

echo "[6/8] Frida server x86_64"
if [ ! -f "$GP/frida-server-x86_64" ]; then
  curl -fsSL --max-time 120 \
    -o "$GP/frida-server.xz" \
    https://github.com/frida/frida/releases/download/16.5.9/frida-server-16.5.9-android-x86_64.xz
  xz -dkf "$GP/frida-server.xz"
  mv -f "$GP/frida-server" "$GP/frida-server-x86_64" 2>/dev/null || true
  chmod 755 "$GP/frida-server-x86_64"
fi

echo "[7/8] Binderfs dan service"
modprobe binder_linux 2>/dev/null || true
mkdir -p /dev/binderfs
cp "$SRC/templates/dev-binderfs.mount" /etc/systemd/system/dev-binderfs.mount
mkdir -p /etc/systemd/system/waydroid-container.service.d
cp "$SRC/templates/waydroid-container-override.conf" \
  /etc/systemd/system/waydroid-container.service.d/override.conf
systemctl daemon-reload
systemctl enable --now dev-binderfs.mount

if [ -n "${TAILSCALE_IP:-}" ]; then
  sed "s/__TAILSCALE_IP__/$TAILSCALE_IP/g" "$SRC/templates/waydroid-adb-relay.service" \
    > /etc/systemd/system/waydroid-adb-relay.service
  systemctl daemon-reload
  systemctl enable --now waydroid-adb-relay.service
fi

if [ -f "$SRC/templates/waydroid-remote.service" ]; then
  sed "s#__ROOT__#$ROOT#g" "$SRC/templates/waydroid-remote.service" \
    > /etc/systemd/system/waydroid-remote.service
  systemctl daemon-reload
  systemctl enable --now waydroid-remote.service
fi

echo "[8/8] Waydroid image"
if [ ! -f /var/lib/waydroid/images/system.img ]; then
  echo "Mengunduh image Waydroid GAPPS. Ini bisa memakan waktu."
  waydroid init -f -s GAPPS
fi

echo
echo "INSTALL SELESAI"
echo "Langkah berikutnya:"
echo "1. Tambah kredensial: $CV/vault add akun1"
echo "2. Start runtime: $GP/start-runtime.sh"
echo "3. Cek: $GP/0_cek.sh"
echo "4. Login Google di Waydroid, lalu jalankan langkah langganan."
echo
echo "Jangan pernah commit key.bin, vault.enc, password, token, atau report."
