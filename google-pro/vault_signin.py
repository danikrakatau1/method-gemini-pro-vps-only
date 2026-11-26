#!/usr/bin/env python3
"""Drive Google sign-in for the vault account with direct adb calls. No secrets printed."""
import re
import subprocess
import sys
import time
import html as htmlmod
import os

sys.path.insert(0, os.environ.get("MTOOL_ROOT", "/srv/meowtools") + "/google-pro")
import vault_run

ADB = "/usr/bin/adb"
SCRATCH = "/root/.hermes/cache/scratch"


def adb(*args, timeout=60):
    return subprocess.run([ADB] + list(args), capture_output=True, timeout=timeout)


def dump(tag):
    remote = f"/sdcard/vs-{tag}.xml"
    local = f"{SCRATCH}/vs-{tag}.xml"
    adb("shell", "uiautomator", "dump", remote)
    adb("pull", remote, local)
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
        out.append({
            "text": htmlmod.unescape(t.group(1)) if t else "",
            "desc": htmlmod.unescape(d.group(1)) if d else "",
            "cls": tag,
            "box": tuple(map(int, b.groups())) if b else None,
        })
    return out


def edit_pos(xml):
    for n in nodes(xml):
        if "EditText" in n["cls"] and n["box"]:
            return (n["box"][0] + n["box"][2]) // 2, (n["box"][1] + n["box"][3]) // 2
    return None


def tap(x, y):
    adb("shell", "input", "tap", str(x), str(y))


def text_of(xml):
    return " | ".join(dict.fromkeys(n["text"].strip() for n in nodes(xml) if n["text"].strip()))


def type_secret(secret):
    adb("shell", "input", "tap", "360", "356")
    time.sleep(0.5)
    adb("shell", "input", "keyevent", "123")
    for _ in range(60):
        adb("shell", "input", "keyevent", "67")
    adb("shell", "input", "text", secret)
    time.sleep(1)


def accounts():
    p = adb("shell", "dumpsys", "account")
    return re.findall(r"Account \{name=([^,]+),", p.stdout.decode("utf-8", "ignore"))


def main():
    rec = vault_run.load()[0]
    email = rec["email"]
    pwd = rec.get("password", "")
    print("TARGET:", email, flush=True)
    print("BEFORE:", accounts(), flush=True)

    adb("shell", "am", "start", "-a", "android.settings.ADD_ACCOUNT_SETTINGS")
    time.sleep(14)
    xml = dump("1")
    print("SCREEN1:", text_of(xml)[:400], flush=True)
    pos = edit_pos(xml)
    if not pos:
        print("STOP: email field tidak muncul", flush=True)
        return 1
    type_secret(email)
    adb("shell", "input", "keyevent", "66")
    time.sleep(10)

    xml = dump("2")
    print("SCREEN2:", text_of(xml)[:400], flush=True)
    pos = edit_pos(xml)
    if not pos:
        print("STOP: password field tidak muncul", flush=True)
        return 1
    tap(*pos)
    time.sleep(0.5)
    adb("shell", "input", "keyevent", "123")
    for _ in range(60):
        adb("shell", "input", "keyevent", "67")
    adb("shell", "input", "text", pwd)
    time.sleep(1)
    adb("shell", "input", "keyevent", "66")
    time.sleep(14)

    got = accounts()
    print("AFTER:", got, flush=True)
    xml = dump("3")
    print("SCREEN3:", text_of(xml)[:600], flush=True)
    return 0 if email.lower() in [a.lower() for a in got] else 2


if __name__ == "__main__":
    sys.exit(main())
