#!/usr/bin/env python3
"""Selesaikan layar password Google yang sedang terbuka, tanpa menampilkan rahasia."""
import os
import sys
import time

BASE = "/srv/meowtools/google-pro"
os.environ["ADB_PATH"] = os.path.join(BASE, "adb-waydroid")
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, BASE)

import ultra0
import vault_run

ultra0.ADB = ultra0.find_adb()
ultra0.pick_device()
rec = vault_run.load()[0]
pos = ultra0.find_edit()
print("edit field:", bool(pos), flush=True)
if not pos:
    raise SystemExit("tidak ada field password di layar")
ultra0.tap(*pos)
time.sleep(0.5)
ultra0.sh("shell", "input keyevent 123")
for _ in range(80):
    ultra0.sh("shell", "input keyevent 67")
ultra0.type_text(rec.get("password", ""))
time.sleep(1)
ultra0.tap_text("Next", "Berikutnya", "Lanjut", "Tiếp theo", "下一步")
time.sleep(8)
print("done, accounts:", ultra0.accounts_on_device(), flush=True)
