#!/bin/bash
# Start all runtime pieces needed by the ported toolkit.
set -e

BASE=${GOOGLE_PRO_DIR:-/srv/meowtools/google-pro}
FRIDA_BIN=${FRIDA_SERVER_BIN:-/srv/meowtools/google-pro/frida-server-x86_64}

# Binderfs
if ! mountpoint -q /dev/binderfs; then
  mount -t binder binder /dev/binderfs
fi
ln -sf /dev/binderfs/binder /dev/binder
ln -sf /dev/binderfs/hwbinder /dev/hwbinder
ln -sf /dev/binderfs/vndbinder /dev/vndbinder

# Headless Weston compositor. ADB screenshot/input does not need a visible X display.
if ! pgrep -f 'weston --backend=headless --renderer=pixman --socket=waydroid-wayland' >/dev/null; then
  rm -f /run/user/0/waydroid-wayland /run/user/0/waydroid-wayland.lock 2>/dev/null || true
  XDG_RUNTIME_DIR=/run/user/0 nohup weston --backend=headless --renderer=pixman \
    --socket=waydroid-wayland --log=/var/lib/waydroid/weston-headless.log >/dev/null 2>&1 &
  sleep 3
fi

# Waydroid session
if ! waydroid status 2>&1 | grep -q '^Session:\s*RUNNING'; then
  XDG_RUNTIME_DIR=/run/user/0 WAYLAND_DISPLAY=waydroid-wayland \
    nohup waydroid session start >/var/lib/waydroid/session.log 2>&1 &
  for i in $(seq 1 40); do
    sleep 2
    waydroid status 2>&1 | grep -q '^Session:\s*RUNNING' && break
  done
fi

# ADB + port forward
if ! /usr/bin/adb devices 2>/dev/null | grep -q '192.168.240.112.*device'; then
  /usr/bin/adb connect 192.168.240.112:5555 >/dev/null 2>&1 || true
fi
/usr/bin/adb forward tcp:27042 tcp:27042 >/dev/null 2>&1 || true
/usr/bin/adb shell wm size 720x1280 >/dev/null 2>&1 || true
/usr/bin/adb shell wm density 240 >/dev/null 2>&1 || true

# Make sure the correct x86_64 frida-server is installed inside Waydroid
if [ -f "$FRIDA_BIN" ]; then
  /usr/bin/adb push "$FRIDA_BIN" /data/local/tmp/frida-server >/dev/null 2>&1 || true
  /usr/bin/adb shell chmod 755 /data/local/tmp/frida-server >/dev/null 2>&1 || true
fi

# frida-server as root inside Waydroid
if ! waydroid shell -- /system/bin/ps -A 2>/dev/null | grep -q frida-server; then
  waydroid shell -- /system/bin/sh -c 'nohup /data/local/tmp/frida-server -l 0.0.0.0:27042 >/dev/null 2>&1 &'
  sleep 2
fi

waydroid status 2>&1 | head -6
/usr/bin/adb devices 2>&1 | head -3
echo "runtime ready"
