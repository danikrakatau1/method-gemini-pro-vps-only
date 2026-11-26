#!/usr/bin/env python3
"""Minimal Flask panel for controlling a local Waydroid instance over ADB.

Bind to 127.0.0.1 only; put Caddy/Nginx with auth in front for remote access.
"""
import io
import os
import re
import shlex
import subprocess
import threading
import time

from flask import Flask, Response, jsonify, request

ADB = os.environ.get("ADB_BIN", "/usr/bin/adb")
SHOT_W = int(os.environ.get("SHOT_W", "540"))
SHOT_H = int(os.environ.get("SHOT_H", "960"))

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024


def logical_size():
    w, h = 720, 1280
    try:
        out = subprocess.run([ADB, "shell", "wm", "size"], capture_output=True,
                             text=True, timeout=10).stdout
        for line in out.splitlines():
            if "Override" in line or "Physical" in line:
                m = re.search(r"(\d+)x(\d+)", line)
                if m:
                    w, h = int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return w, h


def scale_factor():
    lw, lh = logical_size()
    return min(SHOT_W / lw, SHOT_H / lh)


_SHOT_CACHE = {"t": 0.0, "data": None}
SHOT_TTL = float(os.environ.get("SHOT_TTL", "1.0"))
_ADB_LOCK = threading.Lock()


@app.get("/waydroid/api/screenshot")
def screenshot():
    now = time.monotonic()
    if _SHOT_CACHE["data"] and now - _SHOT_CACHE["t"] < SHOT_TTL:
        return Response(_SHOT_CACHE["data"], mimetype="image/jpeg",
                        headers={"Cache-Control": "no-store"})
    try:
        with _ADB_LOCK:
            p = subprocess.run([ADB, "exec-out", "screencap", "-p"],
                               capture_output=True, timeout=20)
    except Exception as e:
        return Response(str(e)[:200], status=502, mimetype="text/plain")
    if p.returncode != 0 or not p.stdout.startswith(b"\x89PNG"):
        return Response("screencap failed", status=502, mimetype="text/plain")
    from PIL import Image
    img = Image.open(io.BytesIO(p.stdout)).convert("RGB")
    img.thumbnail((SHOT_W, SHOT_H), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=55, optimize=True)
    _SHOT_CACHE["data"] = buf.getvalue()
    _SHOT_CACHE["t"] = time.monotonic()
    return Response(_SHOT_CACHE["data"], mimetype="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.get("/waydroid/api/mjpeg")
def mjpeg():
    env = os.environ.copy()
    env["DISPLAY"] = ":100"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error",
           "-f", "x11grab", "-video_size", "1280x800", "-framerate", "8",
           "-i", ":100", "-vf", "scale=480:-1", "-f", "mjpeg", "-q:v", "10", "pipe:1"]

    def gen():
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        assert p.stdout is not None
        buf = b""
        try:
            while True:
                chunk = p.stdout.read(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\xff\xd8" in buf and b"\xff\xd9" in buf:
                    start = buf.find(b"\xff\xd8")
                    end = buf.find(b"\xff\xd9", start)
                    if end < 0:
                        break
                    frame = buf[start:end + 2]
                    buf = buf[end + 2:]
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                           frame + b"\r\n")
        finally:
            p.kill()

    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame",
                    headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no",
                             "Connection": "close"})


@app.post("/waydroid/api/input")
def input_cmd():
    d = request.get_json(silent=True) or {}
    action = d.get("action")
    scale = scale_factor()
    lw, lh = logical_size()

    def conv(v):
        return max(0, min((lw if v % 2 == 0 else lh) - 1, round(v / scale)))

    if action == "tap":
        try:
            x, y = int(d["x"]), int(d["y"])
        except Exception:
            return jsonify({"error": "x/y invalid"}), 400
        args = ["shell", "input", "tap", str(conv(x)), str(conv(y))]
    elif action == "swipe":
        try:
            pts = [int(d[k]) for k in ("x1", "y1", "x2", "y2")]
        except Exception:
            return jsonify({"error": "swipe coords invalid"}), 400
        dur = str(max(100, min(3000, int(d.get("duration", 500)))))
        args = ["shell", "input", "swipe", str(conv(pts[0])), str(conv(pts[1])),
                str(conv(pts[2])), str(conv(pts[3])), dur]
    elif action == "text":
        text = shlex.quote(str(d.get("value", "")).replace(" ", "%s"))
        args = ["shell", "input", "text", text]
    elif action == "keyevent":
        key = str(d.get("key", ""))
        if not key:
            return jsonify({"error": "key missing"}), 400
        args = ["shell", "input", "keyevent", key]
    else:
        return jsonify({"error": "unknown action"}), 400

    err = ""
    for attempt in range(3):
        try:
            with _ADB_LOCK:
                p = subprocess.run([ADB] + args, capture_output=True,
                                   text=True, timeout=30)
            err = (p.stderr or "").strip()
            if p.returncode == 0:
                return jsonify({"ok": True})
        except Exception as e:
            err = str(e)[:200]
        time.sleep(0.4 * (attempt + 1))
    return jsonify({"ok": False, "error": err[:200]})


@app.get("/waydroid/remote")
def remote():
    html = r'''<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Waydroid Remote</title>
<style>
body{margin:0;background:#07090f;color:#eef1f7;font-family:system-ui;padding:12px}
h1{font-size:15px;letter-spacing:.14em;text-transform:uppercase;color:#d8b878;margin:0 0 10px}
img{display:block;width:100%;max-width:540px;border:1px solid #2a3142;border-radius:8px;background:#000;touch-action:manipulation;user-select:none}
.bar{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
input,button{font:inherit;padding:10px 12px;border-radius:8px;border:1px solid #2a3142;background:#101623;color:#fff}
input{flex:1;min-width:180px}button{cursor:pointer;border-color:#d8b878;color:#d8b878;background:transparent}
small{color:#8e98ad;display:block;margin-top:8px}
</style></head><body>
<h1>Waydroid Remote</h1>
<img id="screen" alt="Waydroid screen">
<div class="bar"><input id="txt" placeholder="Teks / kata sandi" autocomplete="off"><button id="sendText">Kirim teks</button></div>
<div class="bar"><input id="key" placeholder="KEYCODE, mis. KEYCODE_BACK"><button id="sendKey">Keyevent</button></div>
<div class="bar"><button id="refresh">Ambil screenshot</button><button id="live">Live ~8fps (tab baru)</button><button id="still">Mode screenshot</button><label style="font-size:12px;color:#8e98ad;display:flex;align-items:center;gap:6px"><input id="auto" type="checkbox" style="flex:0;min-width:0"> Auto refresh</label><span id="coord" style="font:12px ui-monospace,monospace;color:#d8b878"></span></div>
<small>Tekan atau geser gambar untuk kirim tap/swipe. Jangan taruh rahasia di chat.</small>
<script>
const img=document.getElementById('screen'),auto=document.getElementById('auto');
async function refresh(){img.src='/waydroid/api/screenshot?t='+Date.now()}
document.getElementById('refresh').onclick=refresh;
document.getElementById('live').onclick=()=>{auto.checked=false;window.open('/waydroid/api/mjpeg?t='+Date.now(),'_blank')};
document.getElementById('still').onclick=()=>{img.src='';refresh()};
setInterval(()=>{if(auto.checked)refresh()},1800);refresh();
async function post(body){const r=await fetch('/waydroid/api/input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json();if(!j.ok){document.getElementById('coord').textContent='ERROR: '+(j.error||'gagal');}return j}
function at(cx,cy){const r=img.getBoundingClientRect();return{x:Math.round((cx-r.left)*img.naturalWidth/r.width),y:Math.round((cy-r.top)*img.naturalHeight/r.height)}}
let start=null;
img.addEventListener('pointerdown',e=>{e.preventDefault();start={cx:e.clientX,cy:e.clientY};img.setPointerCapture(e.pointerId)});
img.addEventListener('pointerup',e=>{e.preventDefault();if(!start)return;const a=start;start=null;const dx=e.clientX-a.cx,dy=e.clientY-a.cy,p=at(e.clientX,e.clientY);
if(Math.abs(dx)>14||Math.abs(dy)>14){const q=at(a.cx,a.cy);document.getElementById('coord').textContent=q.x+','+q.y+' -> '+p.x+','+p.y;post({action:'swipe',x1:q.x,y1:q.y,x2:p.x,y2:p.y,duration:500}).then(()=>{setTimeout(refresh,800);setTimeout(refresh,1600)})}
else{document.getElementById('coord').textContent=p.x+','+p.y;post({action:'tap',x:p.x,y:p.y}).then(()=>{setTimeout(refresh,800);setTimeout(refresh,1600)})}});
document.getElementById('sendText').onclick=async()=>{const b=document.getElementById('sendText'),v=document.getElementById('txt').value;if(!v)return;b.disabled=true;try{await post({action:'text',value:v});document.getElementById('txt').value='';setTimeout(refresh,800)}finally{b.disabled=false}};
document.getElementById('sendKey').onclick=async()=>{const v=document.getElementById('key').value.trim();if(v){await post({action:'keyevent',key:v});setTimeout(refresh,800)}};
</script></body></html>'''
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8765")), threaded=True)
