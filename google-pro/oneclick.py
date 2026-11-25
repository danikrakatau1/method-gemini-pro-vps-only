#!/usr/bin/env python3
"""One-click runner for the Google AI Pro 12+6+6 month flow.

Usage:
  /usr/bin/python3 oneclick.py --check     # read-only diagnostics, no purchase
  /usr/bin/python3 oneclick.py             # full run, needs explicit go-ahead

Credentials come from the encrypted vault created by vault_add.py.
Nothing secret is read from chat or written to logs.
"""
import argparse
import base64
import datetime
import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import time
import html as htmlmod

BASE = "/srv/meowtools/google-pro"
os.environ["ADB_PATH"] = os.path.join(BASE, "adb-waydroid")
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["FRIDA_ARCH"] = "x86_64"
sys.path.insert(0, BASE)

import ultra0
import vault_run

SERIAL = "192.168.240.112:5555"
ADB = ["/usr/bin/adb", "-s", SERIAL]
SCRATCH = "/root/.hermes/cache/scratch"
TARGET_HASH = None


def ad(*args, timeout=90):
    return subprocess.run(ADB + list(args), capture_output=True, timeout=timeout)


def dump(tag):
    remote, local = f"/sdcard/oc-{tag}.xml", f"{SCRATCH}/oc-{tag}.xml"
    ad("shell", "uiautomator", "dump", remote)
    ad("pull", remote, local)
    try:
        return open(local, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def nodes(xml):
    out = []
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        t = re.search(r'text="([^"]*)"', tag)
        d = re.search(r'content-desc="([^"]*)"', tag)
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        out.append((htmlmod.unescape(t.group(1)) if t else "", htmlmod.unescape(d.group(1)) if d else "", tag,
                    tuple(map(int, b.groups())) if b else None))
    return out


def texts(xml):
    return [htmlmod.unescape(m.group(1)).strip() for m in re.finditer(r'<node[^>]*?text="([^"]*)"[^>]*>', xml) if m.group(1).strip()]


def btn(xml, label):
    for t, d, tag, b in nodes(xml):
        if b and (t == label or d == label):
            return b
    return None


def edit(xml):
    for t, d, tag, b in nodes(xml):
        if b and "EditText" in tag:
            return (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    return None


def edit_value(xml):
    for t, d, tag, b in nodes(xml):
        if b and "EditText" in tag:
            return t
    return None


def wide_bottom(xml):
    best = None
    for t, d, tag, b in nodes(xml):
        if b and 'clickable="true"' in tag and b[1] > 900 and (b[2] - b[0]) > 400:
            if best is None or b[1] > best[1]:
                best = b
    return best


def accounts():
    p = ad("shell", "dumpsys", "account").stdout.decode("utf-8", "ignore")
    return re.findall(r"Account \{name=([^,]+),", p)


def focus():
    p = ad("shell", "dumpsys", "window").stdout.decode("utf-8", "ignore")
    m = re.search(r"mCurrentFocus=Window\{[^}]* u0 ([^/]+)/", p)
    return m.group(1) if m else ""


def key_for(ch):
    lower = {
        "a": 29, "b": 30, "c": 31, "d": 32, "e": 33, "f": 34, "g": 35, "h": 36,
        "i": 37, "j": 38, "k": 39, "l": 40, "m": 41, "n": 42, "o": 43, "p": 44,
        "q": 45, "r": 46, "s": 47, "t": 48, "u": 49, "v": 50, "w": 51, "x": 52,
        "y": 53, "z": 54, "0": 7, "1": 8, "2": 9, "3": 10, "4": 11,
        "5": 12, "6": 13, "7": 14, "8": 15, "9": 16,
        ".": 56, ",": 55, "-": 69, "/": 68, "@": 9, " ": 62,
    }
    if ch in lower:
        return lower[ch], (ch.isupper() or ch == "@")
    if ch.lower() in lower and ch.isupper():
        return lower[ch.lower()], True
    return None, False


def type_secret(secret, pos=None):
    x, y = pos or (360, 470)
    ad("shell", "input", "tap", str(x), str(y))
    time.sleep(0.5)
    ad("shell", "input", "keyevent", "123")
    for _ in range(60):
        ad("shell", "input", "keyevent", "67")
    for ch in secret:
        if ch == "@":
            ad("shell", "input", "text", "@")
            time.sleep(0.04)
            continue
        code, shift = key_for(ch)
        if code is None:
            ad("shell", "input", "text", ch)
            time.sleep(0.04)
            continue
        if shift:
            ad("shell", "input", "keyevent", "59")
        ad("shell", "input", "keyevent", str(code))
        time.sleep(0.04)
    time.sleep(1)


def billing_hash(email):
    return base64.urlsafe_b64encode(hashlib.sha256(email.encode()).digest()).decode().rstrip("=")


def check_billing_account(email):
    ad("shell", "am", "force-stop", "com.google.android.apps.subscriptions.red")
    subprocess.run(["waydroid", "app", "launch", "com.google.android.apps.subscriptions.red"], capture_output=True, timeout=60)
    time.sleep(10)
    log = ad("logcat", "-d", "-v", "threadtime").stdout.decode("utf-8", "ignore")
    hits = re.findall(r"Billing preferred account via installer[^:]*: \[([^\]]+)\]", log)
    want = billing_hash(email)
    return bool(hits) and hits[-1] == want, (hits[-1] if hits else "none"), want


def play_country(email):
    ultra0.sh("shell", f"cp /data/data/com.android.vending/shared_prefs/finsky.xml /data/local/tmp/finsky-oc.xml; chmod 666 /data/local/tmp/finsky-oc.xml", timeout=30)
    ad("pull", "/data/local/tmp/finsky-oc.xml", f"{SCRATCH}/finsky-oc.xml")
    p = f"{SCRATCH}/finsky-oc.xml"
    if not os.path.exists(p):
        return None
    m = re.search(r'account-play-country' + re.escape(email) + r'">([^<]+)<', open(p, encoding="utf-8", errors="replace").read())
    return m.group(1) if m else None


def sku_price():
    pid = ad("shell", "pidof", "com.google.android.apps.subscriptions.red").stdout.decode().strip()
    if not pid:
        return None
    r = ultra0.run_trial(int(pid.split()[0]), wait=20, plan="pro12", list_only=True)
    for o in r.get("offers", []):
        if o.get("id") == "null":
            return int(o.get("micros", 0))
    return None


def lib_valid_until():
    ultra0.sh("shell", "cp /data/data/com.android.vending/databases/library.db /data/local/tmp/lib-oc.db; chmod 666 /data/local/tmp/lib-oc.db", timeout=30)
    ad("pull", "/data/local/tmp/lib-oc.db", f"{SCRATCH}/lib-oc.db")
    p = f"{SCRATCH}/lib-oc.db"
    if not os.path.exists(p):
        return None
    c = sqlite3.connect(p)
    r = c.execute("select subs_valid_until_time from ownership where doc_id like '%subs_variant%'").fetchone()
    c.close()
    return r[0] if r else None


def lib_active_for(email):
    ultra0.sh("shell", "cp /data/data/com.android.vending/databases/library.db /data/local/tmp/lib-active.db; chmod 666 /data/local/tmp/lib-active.db", timeout=30)
    ad("pull", "/data/local/tmp/lib-active.db", f"{SCRATCH}/lib-active.db")
    p = f"{SCRATCH}/lib-active.db"
    if not os.path.exists(p):
        return False
    c = sqlite3.connect(p)
    rows = c.execute("select account,subs_valid_until_time from ownership where doc_id like '%subs_variant%'").fetchall()
    c.close()
    now = int(time.time() * 1000)
    return any(a.lower() == email.lower() and int(v or 0) > now for a, v in rows)


def sign_in(email, password, reset=True):
    if reset:
        # Clear stale auth screens so the email field is really the GMS sign-in field
        ad("shell", "am", "force-stop", "com.google.android.gms")
        ad("shell", "am", "force-stop", "com.google.android.gms.ui")
        ad("shell", "am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME")
        time.sleep(2)
    pos = None
    for i in range(12):
        if i % 3 == 0:
            ad("shell", "am", "start", "-a", "android.settings.ADD_ACCOUNT_SETTINGS")
            time.sleep(2)
        f = focus()
        xml = dump("signin1")
        pos = edit(xml)
        if pos and ("gms" in f or "settings" in f):
            break
        time.sleep(5)
    if not pos:
        print("FAIL: email field tidak muncul (focus: %s)" % focus(), flush=True)
        return False
    type_secret(email, pos)
    for _ in range(3):
        val = edit_value(dump("signin1v")) or ""
        if email.lower() in val.lower():
            break
        type_secret(email, pos)
    ad("shell", "input", "keyevent", "66")
    pos = None
    for _ in range(12):
        xml = dump("signin2")
        pos = edit(xml)
        if pos:
            break
        time.sleep(5)
    if not pos:
        print("FAIL: password field tidak muncul", flush=True)
        return False
    type_secret(password, pos)
    for _ in range(3):
        val = edit_value(dump("signin2v"))
        if val is not None and len(val) == len(password):
            break
        type_secret(password, pos)
    ad("shell", "input", "keyevent", "66")
    time.sleep(3)
    xml_after = dump("signin2submit")
    if edit(xml_after):
        b = btn(xml_after, "Next") or btn(xml_after, "Lanjut") or btn(xml_after, "Continue")
        if b:
            print("Menekan tombol Next password...", flush=True)
            ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
    print("MENUNGGU verifikasi 2FA di HP kamu (bisa sampai 5 menit)...", flush=True)
    code_printed = False
    captcha_printed = False
    for _ in range(60):
        time.sleep(5)
        xml = dump("signinwait")
        joined = " ".join(texts(xml))
        if any(x in joined.lower() for x in (
            "wrong password", "incorrect password", "password is incorrect",
            "that password is wrong", "password tidak salah", "kata sandi salah",
        )):
            print("PASSWORD_SALAH terdeteksi dari layar Google.", flush=True)
            return "WRONG_PASSWORD"
        if any(x in joined.lower() for x in ("try another way", "forgot password")) and "wrong" in joined.lower():
            print("PASSWORD_SALAH terdeteksi dari layar Google.", flush=True)
            return "WRONG_PASSWORD"
        if "not a robot" in joined.lower() or "Confirm you" in joined:
            if not captcha_printed:
                print("CAPTCHA: selesaikan 'Confirm you're not a robot' lewat web remote", flush=True)
                captcha_printed = True
            continue
        if "Couldn’t sign you in" in joined or "couldn't verify this account belongs to you" in joined or "Try again later" in joined:
            print("FAIL: Google menolak verifikasi akun (anti-automation). Tunggu beberapa jam lalu coba lagi.", flush=True)
            return False
        if "Verify it's you" in joined or "Check your phone" in joined:
            if not code_printed:
                code = next((t for t in texts(xml) if re.fullmatch(r"\d{1,3}", t)), None)
                print("LAYAR VERIFIKASI: tap angka di bawah ini di HP kamu ->", code, flush=True)
                code_printed = True
            continue
        b = btn(xml, "I agree") or btn(xml, "Setuju")
        if b:
            ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
            time.sleep(4)
            continue
        b = btn(xml, "Not now")
        if b:
            ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
            time.sleep(3)
            continue
        if email.lower() in [a.lower() for a in accounts()]:
            return True
    return email.lower() in [a.lower() for a in accounts()]


def remove_other_accounts(email):
    for acc in list(accounts()):
        if acc.lower() == email.lower():
            continue
        print("Menghapus akun lama:", acc, flush=True)
        ad("shell", "am", "start", "-a", "android.settings.SETTINGS")
        time.sleep(5)
        for _ in range(3):
            ad("shell", "input", "swipe", "360", "1000", "360", "400", "250")
            time.sleep(1)
        xml = dump("setacc")
        b = None
        for t, d, tag, box in nodes(xml):
            if t == "Passwords & accounts" and box:
                b = box
        if not b:
            print("FAIL: menu Passwords & accounts tidak ketemu", flush=True)
            return False
        ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
        time.sleep(4)
        xml = dump("acclist")
        b = None
        for t, d, tag, box in nodes(xml):
            if t == acc and box:
                b = box
        if not b:
            print("FAIL: baris akun tidak ketemu", flush=True)
            return False
        ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
        time.sleep(4)
        xml = dump("acctdetail")
        b = btn(xml, "Remove account")
        if not b:
            print("FAIL: tombol Remove account tidak ketemu", flush=True)
            return False
        ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
        time.sleep(3)
        xml = dump("removeconf")
        b = btn(xml, "Remove account")
        if b:
            ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
        time.sleep(8)
    return [a.lower() for a in accounts()] == [email.lower()]


def claim(plan, stack, password):
    if ultra0.ADB is None:
        ultra0.ADB = ultra0.find_adb()
        ultra0.SERIAL = SERIAL
    token = ultra0.read_purchase_token("subs_variant") if stack else ""
    pid = ad("shell", "pidof", "com.google.android.apps.subscriptions.red").stdout.decode().strip()
    if not pid:
        subprocess.run(["waydroid", "app", "launch", "com.google.android.apps.subscriptions.red"], capture_output=True, timeout=60)
        time.sleep(7)
        pid = ad("shell", "pidof", "com.google.android.apps.subscriptions.red").stdout.decode().strip()
    if not pid:
        print("FAIL: Google One tidak jalan", flush=True)
        return False
    res = ultra0.run_trial(int(pid.split()[0]), wait=18, plan=plan, stack=stack, old_token=token)
    if (res.get("launched") or {}).get("code") != 0:
        print("FAIL: sheet tidak kebuka", flush=True)
        return False
    xml = dump(f"sheet-{plan}")
    joined = " ".join(dict.fromkeys(texts(xml)))
    print("SHEET", joined[:300], flush=True)
    if not stack and "free trial" not in joined.lower() and "Today Rp 0" not in joined:
        print("FAIL: sheet bukan uji coba gratis — dibatalkan supaya nggak kena tagihan", flush=True)
        return False
    bar = wide_bottom(xml)
    if not bar:
        print("FAIL: slider tidak ketemu", flush=True)
        return False
    y = (bar[1] + bar[3]) // 2
    ad("shell", "input", "swipe", str(bar[0] + 40), str(y), str(bar[2] - 24), str(y), "700")
    time.sleep(9)
    xml = dump("afterslide")
    pos = edit(xml)
    if pos:
        type_secret(password, pos)
        b = btn(xml, "Verify")
        if b:
            ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
        else:
            ad("shell", "input", "keyevent", "66")
        time.sleep(12)
    for label in ("OK", "Got it", "Not now", "Manage", "Save", "Turn on"):
        xml = dump(f"dlg-{label}")
        joined = " ".join(texts(xml))
        b = btn(xml, label)
        if b and any(k in joined for k in ("Payment successful", "backup payment", "Unlock more", "verification setting")):
            ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
            print("DIALOG", label, flush=True)
            time.sleep(5)
    return True


def show_subscription():
    ad("shell", "am", "start", "-n", "com.android.vending/com.google.android.finsky.activities.MainActivity")
    time.sleep(6)
    ad("shell", "input", "tap", "648", "42")
    time.sleep(4)
    ad("shell", "input", "tap", "223", "741")
    time.sleep(4)
    ad("shell", "input", "tap", "396", "341")
    time.sleep(7)
    xml = dump("subscription")
    return " | ".join(dict.fromkeys(texts(xml)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="read-only diagnostics")
    ap.add_argument("--email", help="target account email (default: newest entry in vault)")
    ap.add_argument("--signin-current", action="store_true", help="type credentials into the form already on screen")
    a = ap.parse_args()
    rows = vault_run.load()
    rec = next((r for r in rows if r.get("email") == a.email), None) if a.email else rows[-1]
    if not rec:
        raise SystemExit(f"Email {a.email} tidak ada di vault. Daftar: {[r.get('email') for r in rows]}")
    email, password = rec["email"], rec.get("password", "")
    subprocess.run(["/usr/bin/adb", "connect", SERIAL], capture_output=True, timeout=30)
    ultra0.ADB = ultra0.find_adb()
    ultra0.pick_device()
    ultra0.SERIAL = SERIAL

    print("EMAIL", email, flush=True)
    print("ACCOUNTS", accounts(), flush=True)
    print("PLAY", ultra0.current_play_account(), flush=True)
    print("COUNTRY", play_country(email), flush=True)
    # Query the SKU first: this forces Google One to log the billing account
    price = sku_price()
    ok, got, want = check_billing_account(email)
    print("BILLING_OK", ok, "GOT", got, "WANT", want, flush=True)
    print("SKU_MICROS", price, flush=True)
    v = lib_valid_until()
    print("VALID_UNTIL", datetime.datetime.fromtimestamp(v / 1000, datetime.timezone.utc).isoformat() if v else None, flush=True)
    if a.check:
        return 0
    if a.signin_current:
        print("SIGNIN_CURRENT", sign_in(email, password, reset=False), flush=True)
        print("ACCOUNTS", accounts(), flush=True)
        return 0
    if email.lower() not in [x.lower() for x in accounts()]:
        if not sign_in(email, password):
            print("FAIL: sign-in gagal", flush=True)
            return 1
    if not remove_other_accounts(email):
        print("FAIL: hapus akun lama gagal", flush=True)
        return 1
    ultra0.switch_play(email)
    ok, got, want = check_billing_account(email)
    print("BILLING_OK_AFTER", ok, "GOT", got, "WANT", want, flush=True)
    if not ok:
        print("FAIL: billing masih akun lama setelah akun lama dihapus", flush=True)
        return 1
    price = sku_price()
    print("SKU_MICROS_AFTER", price, flush=True)
    if price != 309000000000:
        print("FAIL: harga SKU bukan Rp 309.000, dibatalkan", flush=True)
        return 1
    if lib_active_for(email):
        print("SKIP: akun ini sudah punya langganan aktif", flush=True)
        print("SUBSCRIPTION", show_subscription()[:900], flush=True)
        return 0
    for plan, stack in (("pro12", False), ("pro6", True), ("pro6b", True)):
        print("CLAIM", plan, "stack" if stack else "new", flush=True)
        if not claim(plan, stack, password):
            return 1
    print("SUBSCRIPTION", show_subscription()[:900], flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
