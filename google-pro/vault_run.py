#!/usr/bin/env python3
"""Ambil kredensial dari vault lokal, lalu jalankan ultra0.py lewat environment.

Pemakaian:
  /usr/bin/python3 vault_run.py                 # lihat daftar email di vault
  /usr/bin/python3 vault_run.py --email X --list   # cek offer saja (aman)
  /usr/bin/python3 vault_run.py --email X           # jalankan klaim pro12
"""
import argparse
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = Path(os.environ.get("MTOOL_ROOT", "/srv/meowtools")) / "google-pro"
KEY = BASE / ".vault/key.bin"
DATA = BASE / ".vault/accounts.enc"


def load() -> list:
    if not KEY.exists() or not DATA.exists():
        raise SystemExit("Vault belum dibuat. Jalankan: /usr/bin/python3 " + str(BASE / "vault_add.py"))
    blob = DATA.read_bytes()
    return json.loads(AESGCM(KEY.read_bytes()).decrypt(blob[:12], blob[12:], None))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", help="email akun yang dipakai")
    ap.add_argument("--plan", default="pro12")
    ap.add_argument("--list", action="store_true", help="hanya tampilkan offer, aman")
    ap.add_argument("--no-add", action="store_true", help="akun sudah login di perangkat")
    ap.add_argument("--no-force", action="store_true", help="jangan lewati pengecekan/perpindahan akun Play")
    ap.add_argument("--stack", action="store_true", help="tumpuk masa aktif via upgrade Play Billing")
    ap.add_argument("--mode", type=int, default=None, help="mode proration (5=CHARGE_FULL_PRICE)")
    a = ap.parse_args()
    rows = load()
    if not a.email:
        for r in rows:
            print(r.get("email", ""))
        return 0
    rec = next((r for r in rows if r.get("email") == a.email), None)
    if not rec:
        print("Email tidak ada di vault. Daftar:", [r.get("email") for r in rows], file=sys.stderr)
        return 1

    card = rec.get("card") or {}
    env = os.environ.copy()
    env.update({
        "CRED_EMAIL": rec.get("email", ""),
        "CRED_PASSWORD": rec.get("password", ""),
        "CRED_TOTP": rec.get("totp", ""),
        "CRED_CARD_NUMBER": card.get("number", ""),
        "CRED_CARD_EXP": card.get("exp", ""),
        "CRED_CARD_CVC": card.get("cvc", ""),
        "CRED_CARD_HOLDER": card.get("holder", ""),
        "CRED_CARD_ZIP": card.get("zip", ""),
        "ADB_PATH": str(BASE / "adb-waydroid"),
        "PYTHONIOENCODING": "utf-8",
        "FRIDA_ARCH": "x86_64",
    })
    cmd = [sys.executable, str(BASE / "ultra0.py"), "--account-env", "--plan", a.plan]
    if not a.no_force:
        cmd.append("--force")
    if a.list:
        cmd.append("--list")
    if a.no_add:
        cmd.append("--no-add")
    if a.stack:
        cmd.append("--stack")
    if a.mode is not None:
        cmd.extend(["--mode", str(a.mode)])
    print(f"Menjalankan untuk {a.email} (mode {'list' if a.list else ('stack' if a.stack else 'klaim')})...")
    os.execvpe(sys.executable, cmd, env)


if __name__ == "__main__":
    sys.exit(main())
