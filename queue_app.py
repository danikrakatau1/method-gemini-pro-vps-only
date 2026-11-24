#!/usr/bin/env python3
"""Multi-user job queue for Waydroid toolkit.

Secrets policy:
- Web account passwords are stored only as bcrypt hashes.
- Google passwords are never written to DB, logs, or chat; kept in memory only
  while the job is being started, then passed to the child via environment.
"""
import fcntl
import io
import os
import re
import secrets
import shlex
import sqlite3
import subprocess
import threading
import time
from pathlib import Path

import bcrypt
from flask import Flask, Response, jsonify, redirect, request, session, url_for

BASE = Path(os.environ.get("QUEUE_DIR", "/srv/meowtools/gemini_queue"))
DB = BASE / "queue.db"
SECRET_FILE = BASE / "secret.key"
LOCK_FILE = BASE / "worker.lock"
LOG_DIR = BASE / "logs"
LOG_DIR.mkdir(mode=0o700, exist_ok=True)

ADB = os.environ.get("ADB_BIN", "/usr/bin/adb")
PYTHON = os.environ.get("PYTHON_BIN", "/usr/bin/python3")
GP = Path(os.environ.get("GOOGLE_PRO_DIR", "/srv/meowtools/google-pro"))
ULTRA = GP / "ultra0.py"
ADB_WRAPPER = str(GP / "adb-waydroid")
SHOT_W = int(os.environ.get("SHOT_W", "540"))
SHOT_H = int(os.environ.get("SHOT_H", "960"))
BASE_PATH = os.environ.get("BASE_PATH", "/geminitoddd2tahun").rstrip("/")
WORKER_ENABLED = os.environ.get("WORKER_ENABLED", "1") != "0"
BIND_HOST = os.environ.get("BIND_HOST", "127.0.0.1")

app = Flask(__name__)
app.secret_key = SECRET_FILE.read_bytes()
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

JOB_LOCK = threading.Lock()
SECRETS = {}
PROC = None
CURRENT_JOB_ID = None
STOP = threading.Event()

VALID_PLANS = {"auto", "5x", "20x", "pro12", "pro6", "pro6b", "pro6c"}


def db():
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = db()
    con.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        pw_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        google_email TEXT NOT NULL,
        plan TEXT NOT NULL,
        stack INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        started_at TEXT,
        finished_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    con.commit()
    con.close()
    os.chmod(DB, 0o600)


init_db()
os.chmod(DB, 0o600)


def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    con = db()
    row = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    con.close()
    return row


def require_user():
    u = current_user()
    if not u:
        return None
    return u


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


def sanitize_tail(text):
    lines = [ln for ln in text.splitlines()
             if "token=" not in ln.lower() and "purchaseToken" not in ln]
    return "\n".join(lines)[-1200:]


def job_by_id(job_id):
    con = db()
    row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    con.close()
    return row


def update_job(job_id, **fields):
    fields["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    sets = ",".join(f"{k}=?" for k in fields)
    con = db()
    con.execute(f"UPDATE jobs SET {sets} WHERE id=?", (*fields.values(), job_id))
    con.commit()
    con.close()


def user_job(uid):
    con = db()
    row = con.execute(
        "SELECT * FROM jobs WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)
    ).fetchone()
    con.close()
    return row


def queue_position(job_id):
    con = db()
    n = con.execute(
        "SELECT COUNT(*) c FROM jobs WHERE status='queued' AND id < ?", (job_id,)
    ).fetchone()["c"]
    con.close()
    return n + 1


def start_process(job_id, row, google_password):
    global PROC, CURRENT_JOB_ID
    env = os.environ.copy()
    env.update({
        "ADB_PATH": ADB_WRAPPER,
        "PYTHONIOENCODING": "utf-8",
        "FRIDA_ARCH": "x86_64",
        "CRED_EMAIL": row["google_email"],
        "CRED_PASSWORD": google_password or "",
        "CRED_TOTP": "",
    })
    cmd = [PYTHON, str(ULTRA), "--account-env"]
    if row["stack"]:
        cmd.append("--stack")
    cmd += ["--plan", row["plan"]]
    if not google_password:
        cmd += ["--force", "--no-add"]

    log_path = LOG_DIR / f"job-{job_id}.log"
    log = open(log_path, "ab", buffering=0)
    os.chmod(log_path, 0o600)
    PROC = subprocess.Popen(
        cmd, env=env, stdin=subprocess.PIPE, stdout=log,
        stderr=subprocess.STDOUT, cwd=str(GP), start_new_session=True
    )
    CURRENT_JOB_ID = job_id
    update_job(job_id, status="running", note="Memulai otomatisasi...",
               started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def monitor_current():
    global PROC, CURRENT_JOB_ID
    if PROC is None or CURRENT_JOB_ID is None:
        return
    job_id = CURRENT_JOB_ID
    log_path = LOG_DIR / f"job-{job_id}.log"
    try:
        tail = log_path.read_text(encoding="utf-8", errors="ignore")[-6000:]
    except Exception:
        tail = ""

    low = tail.lower()
    if ("perlu tindakan manual" in low or "verify it's you" in low
            or "confirm you're not a robot" in low or "captcha" in low):
        update_job(job_id, status="waiting_human",
                   note="Perlu tindakanmu: selesaikan verifikasi di layar, lalu tekan Lanjut.")

    rc = PROC.poll()
    if rc is None:
        return

    clean = sanitize_tail(tail)
    if rc == 0 and "traceback" not in low:
        status, note = "done", "Selesai."
    else:
        status, note = "failed", "Script berhenti. Silakan coba lagi."
    update_job(job_id, status=status, note=note,
               finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    try:
        PROC.stdin.close()
    except Exception:
        pass
    SECRETS.pop(job_id, None)
    PROC = None
    CURRENT_JOB_ID = None


def worker():
    while not STOP.wait(2):
        if not WORKER_ENABLED:
            continue
        with JOB_LOCK:
            if PROC is not None:
                monitor_current()
                continue
            con = db()
            row = con.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY id LIMIT 1"
            ).fetchone()
            con.close()
            if not row:
                continue
            pw = SECRETS.pop(row["id"], None)
            if not pw and not row["google_email"]:
                update_job(row["id"], status="failed", note="Email belum diisi.")
                continue
            try:
                start_process(row["id"], row, pw)
            except Exception:
                update_job(row["id"], status="failed", note="Gagal memulai worker.")


threading.Thread(target=worker, daemon=True).start()

PAGE = r'''<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gemini 2 Tahun - Antrean</title>
<style>
body{margin:0;background:#080b12;color:#eef2f8;font-family:system-ui;padding:14px}
.card{max-width:760px;margin:auto;background:#101624;border:1px solid #263049;border-radius:14px;padding:18px}
h1{font-size:17px;color:#d8b878;letter-spacing:.08em;margin:0 0 12px}
label{display:block;font-size:11px;color:#9aa6bd;text-transform:uppercase;letter-spacing:.12em;margin:10px 0 6px}
input,select,textarea{width:100%;box-sizing:border-box;padding:11px;border-radius:8px;border:1px solid #2b3650;background:#0a0e18;color:#fff;font:inherit}
button{margin-top:12px;padding:11px 16px;border-radius:8px;border:1px solid #d8b878;background:transparent;color:#d8b878;cursor:pointer}
button.primary{background:#d8b878;color:#080b12}
.row{display:flex;gap:8px;flex-wrap:wrap}.row>*{flex:1;min-width:140px}
#screen{width:100%;max-width:540px;border:1px solid #2b3650;border-radius:8px;background:#000;touch-action:manipulation;user-select:none;margin-top:12px}
.status{padding:12px;border-radius:8px;background:#0a0e18;border:1px solid #263049;margin-top:12px}
small{color:#8b97ad;display:block;margin-top:10px}
a{color:#79e4dd}.err{color:#ff8b7a;font-size:12px}.hide{display:none}
</style></head><body><div class="card">
<h1>GEMINI 2 TAHUN - ANTREAN</h1>
__BODY__
</div></body></html>'''


def page(body):
    return Response(PAGE.replace("__BODY__", body.replace("__BASE__", BASE_PATH)), mimetype="text/html", headers={"Cache-Control":"no-store"})


LOGIN_BODY = r'''<h2>Masuk</h2>
<form method="post" action="__BASE__/login">
<label>Username</label><input name="username" required>
<label>Kata sandi web</label><input name="password" type="password" required>
<button class="primary" type="submit">Masuk</button>
</form>
<p>Belum punya akun? <a href="__BASE__/register">Daftar</a></p>
<p class="err">__ERR__</p>
<small>Kata sandi web hanya disimpan sebagai hash. Kata sandi Google tidak pernah disimpan.</small>'''

REG_BODY = r'''<h2>Daftar akun web</h2>
<form method="post" action="__BASE__/register">
<label>Username</label><input name="username" required>
<label>Kata sandi web</label><input name="password" type="password" required>
<button class="primary" type="submit">Daftar</button>
</form>
<p>Sudah punya akun? <a href="__BASE__/login">Masuk</a></p>
<p class="err">__ERR__</p>'''

DASH_BODY = r'''<p>Halo, <b>__USER__</b>. <a href="__BASE__/logout">Keluar</a></p>
<div class="status" id="status">Memuat status...</div>
<h2>Kirim job</h2>
<form id="jobForm">
<label>Email Google</label><input name="google_email" type="email" required>
<label>Kata sandi Google</label><input name="google_password" type="password" autocomplete="off">
<small>Dipakai sekali untuk login, lalu dibuang. Tidak disimpan.</small>
<div class="row">
<div><label>Plan</label><select name="plan">
<option value="pro12">pro12 - 12 bulan</option>
<option value="pro6">pro6 - tambah 6 bulan</option>
<option value="pro6b">pro6b - tambah 6 bulan lagi</option>
<option value="auto">auto</option>
</select></div>
<div><label>Stack</label><select name="stack">
<option value="1">Ya, timber (disarankan)</option>
<option value="0">Tidak</option>
</select></div>
</div>
<button class="primary" type="submit">Masuk antrean</button>
</form>
<p class="err" id="joberr"></p>
<div id="control" class="hide">
<h2>Layar perangkat</h2>
<img id="screen" alt="Layar Waydroid">
<div class="row"><input id="txt" placeholder="Teks / kata sandi"><button id="sendText">Kirim teks</button></div>
<div class="row"><input id="key" placeholder="KEYCODE_BACK"><button id="sendKey">Keyevent</button></div>
<button id="refresh">Ambil screenshot</button>
<button class="primary" id="done">Lanjut setelah verifikasi</button>
<p class="err" id="ctrlerr"></p>
<small>Tekan atau geser gambar untuk tap atau swipe. Koordinat otomatis.</small>
</div>
<script>
const st=document.getElementById('status'),ctl=document.getElementById('control');
let jobId=null,canControl=false;
async function load(){
 const r=await fetch('__BASE__/status'); const j=await r.json();
 if(!j.user){location.href='__BASE__/login';return}
 if(!j.job){st.textContent='Belum ada job. Kirim job di bawah.';ctl.classList.add('hide');return}
 jobId=j.job.id;canControl=j.job.can_control;
 st.innerHTML='<b>Status:</b> '+j.job.status+'<br><b>Antrean:</b> '+(j.job.queue_position||'-')+'<br><b>Catatan:</b> '+j.job.note;
 if(canControl){ctl.classList.remove('hide');refresh()}else{ctl.classList.add('hide')}
}
async function refresh(){if(!canControl)return;const img=document.getElementById('screen');img.src='__BASE__/screen?t='+Date.now()}
async function post(){}
document.getElementById('jobForm').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);const b={google_email:f.get('google_email'),google_password:f.get('google_password'),plan:f.get('plan'),stack:parseInt(f.get('stack')||'0')};const r=await fetch('__BASE__/job',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});const j=await r.json();if(!r.ok){document.getElementById('joberr').textContent=j.error||'Gagal';return}document.getElementById('joberr').textContent='';e.target.reset();load()};
document.getElementById('refresh').onclick=refresh;
const img=document.getElementById('screen');let start=null;
img.addEventListener('pointerdown',e=>{e.preventDefault();start={x:e.clientX,y:e.clientY};img.setPointerCapture(e.pointerId)});
img.addEventListener('pointerup',async e=>{e.preventDefault();if(!start)return;const a=start;start=null;const dx=e.clientX-a.x,dy=e.clientY-a.y;const r=img.getBoundingClientRect();const P=(cx,cy)=>({x:Math.round((cx-r.left)*img.naturalWidth/r.width),y:Math.round((cy-r.top)*img.naturalHeight/r.height)});let body;if(Math.abs(dx)>14||Math.abs(dy)>14){const q=P(a.x,a.y),p=P(e.clientX,e.clientY);body={action:'swipe',x1:q.x,y1:q.y,x2:p.x,y2:p.y}}else{const p=P(e.clientX,e.clientY);body={action:'tap',x:p.x,y:p.y}}await fetch('__BASE__/input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});refresh()});
document.getElementById('sendText').onclick=async()=>{const v=document.getElementById('txt').value;if(!v)return;await fetch('__BASE__/input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'text',value:v})});document.getElementById('txt').value='';refresh()};
document.getElementById('sendKey').onclick=async()=>{const v=document.getElementById('key').value.trim();if(!v)return;await fetch('__BASE__/input',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'keyevent',key:v})});refresh()};
document.getElementById('done').onclick=async()=>{const r=await fetch('__BASE__/done',{method:'POST'});const j=await r.json();document.getElementById('ctrlerr').textContent=j.error||'';load()};
setInterval(load,2500);load();
</script>'''


@app.get("/")
def home():
    u = require_user()
    if not u:
        return page(LOGIN_BODY.replace("__ERR__", ""))
    return page(DASH_BODY.replace("__USER__", u["username"]))


@app.get("/register")
def register_page():
    return page(REG_BODY.replace("__ERR__", ""))


@app.post("/register")
def register():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    if not username or not password or len(password) < 6:
        return page(REG_BODY.replace("__ERR__", "Username dan password minimal 6 karakter."))
    pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        con = db()
        con.execute("INSERT INTO users(username,pw_hash) VALUES(?,?)", (username, pw))
        con.commit()
        uid = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()["id"]
        con.close()
    except sqlite3.IntegrityError:
        return page(REG_BODY.replace("__ERR__", "Username sudah dipakai."))
    session["uid"] = uid
    return redirect(BASE_PATH + "/")


@app.post("/login")
def login():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    con = db()
    row = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    con.close()
    if not row or not bcrypt.checkpw(password.encode(), row["pw_hash"].encode()):
        return page(LOGIN_BODY.replace("__ERR__", "Login gagal."))
    session["uid"] = row["id"]
    return redirect(BASE_PATH + "/")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(BASE_PATH + "/")


@app.get("/status")
def status_api():
    u = require_user()
    if not u:
        return jsonify({"user": None}), 401
    row = user_job(u["id"])
    if not row:
        return jsonify({"user": u["username"], "job": None})
    return jsonify({"user": u["username"], "job": {
        "id": row["id"],
        "status": row["status"],
        "note": row["note"],
        "queue_position": queue_position(row["id"]) if row["status"] == "queued" else 0,
        "can_control": row["status"] in ("running", "waiting_human")
                       and CURRENT_JOB_ID == row["id"],
    }})


@app.post("/job")
def submit_job():
    u = require_user()
    if not u:
        return jsonify({"error": "Belum login."}), 401
    d = request.get_json(silent=True) or {}
    email = str(d.get("google_email", "")).strip()
    plan = str(d.get("plan", "auto"))
    stack = 1 if str(d.get("stack", "1")) in ("1", "true", "True") else 0
    if not email or "@" not in email:
        return jsonify({"error": "Email Google tidak valid."}), 400
    if plan not in VALID_PLANS:
        return jsonify({"error": "Plan tidak valid."}), 400

    con = db()
    cur = con.execute(
        "INSERT INTO jobs(user_id,google_email,plan,stack,status,note) VALUES(?,?,?,?,?,?)",
        (u["id"], email, plan, stack, "queued", "Menunggu giliran.")
    )
    jid = cur.lastrowid
    con.commit()
    con.close()

    gpw = str(d.get("google_password", ""))
    if gpw:
        SECRETS[jid] = gpw
    return jsonify({"ok": True, "job_id": jid, "queue_position": queue_position(jid)})


@app.get("/screen")
def screen():
    u = require_user()
    if not u:
        return Response("unauthorized", status=401)
    row = user_job(u["id"])
    if not row or row["status"] not in ("running", "waiting_human") or CURRENT_JOB_ID != row["id"]:
        return Response("forbidden", status=403)
    try:
        p = subprocess.run([ADB, "exec-out", "screencap", "-p"],
                           capture_output=True, timeout=20)
    except Exception as e:
        return Response(str(e)[:200], status=502)
    if p.returncode != 0 or not p.stdout.startswith(b"\x89PNG"):
        return Response("screencap failed", status=502)
    from PIL import Image
    img = Image.open(io.BytesIO(p.stdout)).convert("RGB")
    img.thumbnail((SHOT_W, SHOT_H), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=68, optimize=True)
    return Response(buf.getvalue(), mimetype="image/jpeg",
                    headers={"Cache-Control": "no-store"})


@app.post("/input")
def input_cmd():
    u = require_user()
    if not u:
        return jsonify({"error": "Belum login."}), 401
    row = user_job(u["id"])
    if not row or row["status"] not in ("running", "waiting_human") or CURRENT_JOB_ID != row["id"]:
        return jsonify({"error": "Bukan giliranmu."}), 403
    d = request.get_json(silent=True) or {}
    action = d.get("action")
    scale = scale_factor()
    lw, lh = logical_size()

    def conv(v):
        return max(0, min((lw if v % 2 == 0 else lh) - 1, round(v / scale)))

    if action == "tap":
        try:
            args = ["shell", "input", "tap", str(conv(int(d["x"]))), str(conv(int(d["y"])))]
        except Exception:
            return jsonify({"error": "Koordinat invalid."}), 400
    elif action == "swipe":
        try:
            pts = [int(d[k]) for k in ("x1", "y1", "x2", "y2")]
        except Exception:
            return jsonify({"error": "Koordinat invalid."}), 400
        dur = str(max(100, min(3000, int(d.get("duration", 500)))))
        args = ["shell", "input", "swipe", str(conv(pts[0])), str(conv(pts[1])),
                str(conv(pts[2])), str(conv(pts[3])), dur]
    elif action == "text":
        args = ["shell", "input", "text", shlex.quote(str(d.get("value", "")).replace(" ", "%s"))]
    elif action == "keyevent":
        key = str(d.get("key", ""))
        if not key:
            return jsonify({"error": "Key kosong."}), 400
        args = ["shell", "input", "keyevent", key]
    else:
        return jsonify({"error": "Aksi tidak dikenal."}), 400

    try:
        subprocess.run([ADB] + args, capture_output=True, timeout=20)
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 500
    return jsonify({"ok": True})


@app.post("/done")
def done():
    global PROC
    u = require_user()
    if not u:
        return jsonify({"error": "Belum login."}), 401
    row = user_job(u["id"])
    if not row or row["status"] != "waiting_human" or CURRENT_JOB_ID != row["id"]:
        return jsonify({"error": "Tidak ada job yang menunggu tindakanmu."}), 403
    if PROC is not None and PROC.poll() is None and PROC.stdin:
        try:
            PROC.stdin.write(b"\n")
            PROC.stdin.flush()
        except Exception:
            pass
    update_job(row["id"], status="running", note="Verifikasi dikirim, melanjutkan...")
    return jsonify({"ok": True})


if __name__ == "__main__":
    lock = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("Worker queue sudah berjalan.")
    app.run(host=BIND_HOST, port=int(os.environ.get("PORT", "8766")), threaded=True)
