#!/usr/bin/env python3
"""Tambahkan akun dari vault ke perangkat dan pindahkan Play Store ke akun itu."""
import os
import sys

BASE = "/srv/meowtools/google-pro"
os.environ["ADB_PATH"] = os.path.join(BASE, "adb-waydroid")
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["FRIDA_ARCH"] = "x86_64"
sys.path.insert(0, BASE)

import ultra0
import vault_run

email = sys.argv[1] if len(sys.argv) > 1 else None
rows = vault_run.load()
rec = next((r for r in rows if r.get("email") == email), None) if email else (rows[0] if rows else None)
if not rec:
    raise SystemExit("Akun tidak ditemukan di vault")

ultra0.ADB = ultra0.find_adb()
ultra0.pick_device()
ultra0.ensure_root()
ultra0.ensure_network()
ultra0.ensure_frida_server()
ultra0.ensure_module_apk()
ultra0.ensure_vending()

print("TARGET:", rec["email"], flush=True)
print("ADD_ACCOUNT:", ultra0.add_account(rec["email"], rec.get("password", ""), rec.get("totp", "")), flush=True)
print("SWITCH_PLAY:", ultra0.switch_play(rec["email"]), flush=True)
print("CURRENT_PLAY:", ultra0.current_play_account(), flush=True)
print("ACCOUNTS:", ultra0.accounts_on_device(), flush=True)
