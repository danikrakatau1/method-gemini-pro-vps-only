#!/usr/bin/env python3
"""Launch a Play Billing upgrade sheet and finish the slide/password flow manually."""
import os
import re
import subprocess
import sys
import time
import html as htmlmod

BASE = os.environ.get("MTOOL_ROOT", "/srv/meowtools") + "/google-pro"
os.environ["ADB_PATH"] = os.path.join(BASE, "adb-waydroid")
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["FRIDA_ARCH"] = "x86_64"
sys.path.insert(0, BASE)

import ultra0
import vault_run

ADB = ["/usr/bin/adb", "-s", "192.168.240.112:5555"]
SCRATCH = "/root/.hermes/cache/scratch"
PLAN = sys.argv[1] if len(sys.argv) > 1 else "pro6"


def ad(*args, timeout=60):
    return subprocess.run(ADB + list(args), capture_output=True, timeout=timeout)


def dump(tag):
    remote = f"/sdcard/sd-{tag}.xml"
    local = f"{SCRATCH}/sd-{tag}.xml"
    ad("shell", "uiautomator", "dump", remote)
    ad("pull", remote, local)
    try:
        return open(local, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def texts(xml):
    return [htmlmod.unescape(m.group(1)).strip() for m in re.finditer(r'<node[^>]*?text="([^"]*)"[^>]*>', xml) if m.group(1).strip()]


def nodes(xml):
    out = []
    for m in re.finditer(r"<node[^>]*>", xml):
        tag = m.group(0)
        t = re.search(r'text="([^"]*)"', tag)
        d = re.search(r'content-desc="([^"]*)"', tag)
        b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        out.append((htmlmod.unescape(t.group(1)) if t else "", htmlmod.unescape(d.group(1)) if d else "", tag, tuple(map(int, b.groups())) if b else None))
    return out


def wide_bottom(xml):
    for t, d, tag, b in nodes(xml):
        if b and 'clickable="true"' in tag and b[1] > 900 and (b[2] - b[0]) > 400:
            return b
    return None


def btn(xml, label):
    for t, d, tag, b in nodes(xml):
        if b and (t == label or d == label):
            return b
    return None


def edit(xml):
    for t, d, tag, b in nodes(xml):
        if b and "EditText" in tag:
            return b
    return None


def main():
    rec = vault_run.load()[0]
    pwd = rec.get("password", "")
    ultra0.ADB = ultra0.find_adb()
    ultra0.pick_device()
    email = rec["email"]
    print("ACCOUNT", ultra0.current_play_account(), flush=True)
    tok = ultra0.read_purchase_token("subs_variant")
    print("TOKEN", bool(tok), flush=True)
    if not tok:
        return 1
    pid = ultra0.launch_app()
    if not pid:
        subprocess.run(["waydroid", "app", "launch", "com.google.android.apps.subscriptions.red"], capture_output=True, timeout=60)
        time.sleep(7)
        out = ad("shell", "pidof", "com.google.android.apps.subscriptions.red").stdout.decode().strip()
        pid = int(out.split()[0]) if out and out.split()[0].isdigit() else 0
    print("PID", pid, flush=True)
    if not pid:
        return 1
    res = ultra0.run_trial(pid, wait=18, plan=PLAN, stack=True, old_token=tok)
    print("LAUNCHED", res.get("launched"), flush=True)
    if not (res.get("launched") or {}).get("code") == 0:
        return 2

    xml = dump("sheet")
    print("SHEET", " | ".join(dict.fromkeys(texts(xml)))[:500], flush=True)
    bar = wide_bottom(xml)
    print("SLIDER", bar, flush=True)
    if not bar:
        return 3
    y = (bar[1] + bar[3]) // 2
    ad("shell", "input", "swipe", str(bar[0] + 40), str(y), str(bar[2] - 24), str(y), "700")
    time.sleep(9)
    xml = dump("afterslide")
    print("AFTER_SLIDE", " | ".join(dict.fromkeys(texts(xml)))[:400], flush=True)

    eb = edit(xml)
    if eb:
        x, y = (eb[0] + eb[2]) // 2, (eb[1] + eb[3]) // 2
        ad("shell", "input", "tap", str(x), str(y))
        time.sleep(0.5)
        ad("shell", "input", "keyevent", "123")
        for _ in range(60):
            ad("shell", "input", "keyevent", "67")
        ad("shell", "input", "text", pwd)
        time.sleep(1)
        vb = btn(xml, "Verify")
        if vb:
            ad("shell", "input", "tap", str((vb[0] + vb[2]) // 2), str((vb[1] + vb[3]) // 2))
        else:
            ad("shell", "input", "keyevent", "66")
        time.sleep(12)
        xml = dump("afterverify")
        print("AFTER_VERIFY", " | ".join(dict.fromkeys(texts(xml)))[:500], flush=True)

    for label in ("OK", "Got it", "Turn on", "Save", "Manage"):
        xml = dump(f"dlg{label}")
        b = btn(xml, label)
        if b and any(k in " ".join(texts(xml)) for k in ("Payment successful", "backup payment", "verification setting")):
            ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
            print("TAPPED", label, flush=True)
            time.sleep(5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
