#!/bin/bash
# Start all runtime pieces needed by the ported toolkit.
set -e

BASE="${MTOOL_ROOT:-/srv/meowtools}/google-pro"
SCRATCH_DIR="${SCRATCH_DIR:-$HOME/.hermes/cache/scratch}"
FRIDA_BIN="$SCRATCH_DIR/frida-server-x86_64"
[ -s "$FRIDA_BIN" ] || FRIDA_BIN=$BASE/frida-server-x86_64

# Binderfs
if ! mountpoint -q /dev/binderfs; then
  mount -t binder binder /dev/binderfs
fi
ln -sf /dev/binderfs/binder /dev/binder
ln -sf /dev/binderfs/hwbinder /dev/hwbinder
ln -sf /dev/binderfs/vndbinder /dev/vndbinder
mkdir -p /run/user/0/pulse && touch /run/user/0/pulse/native && chmod 666 /run/user/0/pulse/native

# Xvfb :100 must exist before weston starts
if ! pgrep -f "Xvfb :100" >/dev/null; then
  nohup Xvfb :100 -screen 0 1280x800x24 +extension RANDR +render -noreset \
    >/var/log/xvfb-waydroid.log 2>&1 &
  sleep 2
fi
export DISPLAY=:100

# Weston X11 compositor on :100 (started by sgdesk-waydroid-xvfb + manual weston)
if ! pgrep -f 'weston --backend=x11 --renderer=pixman --socket=waydroid-wayland-x11' >/dev/null; then
  XDG_RUNTIME_DIR=/run/user/0 DISPLAY=:100 nohup weston --backend=x11 --renderer=pixman \
    --socket=waydroid-wayland-x11 --log=/var/lib/waydroid/weston-x11.log >/dev/null 2>&1 &
  sleep 3
fi

# Waydroid session
if ! ip link show waydroid0 >/dev/null 2>&1; then
  /usr/lib/waydroid/data/scripts/waydroid-net.sh stop 2>/dev/null || true
  /usr/lib/waydroid/data/scripts/waydroid-net.sh start
fi
if ! waydroid status 2>&1 | grep -q '^Session:\s*RUNNING'; then
  XDG_RUNTIME_DIR=/run/user/0 WAYLAND_DISPLAY=waydroid-wayland-x11 \
    nohup waydroid session start >/var/lib/waydroid/session.log 2>&1 &
  for i in $(seq 1 40); do
    sleep 2
    waydroid status 2>&1 | grep -q '^Session:\s*RUNNING' && break
  done
  if ! waydroid status 2>&1 | grep -q '^Session:\s*RUNNING'; then
    systemctl restart waydroid-container >/dev/null 2>&1 || true
    sleep 5
    /usr/lib/waydroid/data/scripts/waydroid-net.sh start >/dev/null 2>&1 || true
    XDG_RUNTIME_DIR=/run/user/0 WAYLAND_DISPLAY=waydroid-wayland-x11 \
      nohup waydroid session start >/var/lib/waydroid/session.log 2>&1 &
    for i in $(seq 1 40); do
      sleep 2
      waydroid status 2>&1 | grep -q '^Session:\s*RUNNING' && break
    done
  fi
fi

# ADB + port forward
waydroid container unfreeze >/dev/null 2>&1 || true
if ! /usr/bin/adb devices 2>/dev/null | grep -q '192.168.240.112.*device'; then
  waydroid shell -- /system/bin/sh -c 'setprop service.adb.tcp.port 5555; stop adbd; start adbd' >/dev/null 2>&1 || true
  sleep 4
fi
if ! /usr/bin/adb devices 2>/dev/null | grep -q '192.168.240.112.*device'; then
  /usr/bin/adb connect 192.168.240.112:5555 >/dev/null 2>&1 || true
fi
/usr/bin/adb forward tcp:27042 tcp:27042 >/dev/null 2>&1 || true
/usr/bin/adb shell wm size 720x1280 >/dev/null 2>&1 || true
/usr/bin/adb shell wm density 240 >/dev/null 2>&1 || true
# Cegah Android tidur -> Waydroid ikut freeze container (suspend_action=freeze)
/usr/bin/adb shell svc power stayon true >/dev/null 2>&1 || true
/usr/bin/adb shell settings put system screen_off_timeout 2147483647 >/dev/null 2>&1 || true

if [ -f "$BASE/module_521.apk" ]; then
  /usr/bin/adb push "$BASE/module_521.apk" /data/local/tmp/module_521.apk >/dev/null 2>&1 || true
  /usr/bin/adb shell chmod 666 /data/local/tmp/module_521.apk >/dev/null 2>&1 || true
fi

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
