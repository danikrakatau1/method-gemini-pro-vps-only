#!/usr/bin/env python3
"""Interactive one-click console for the Waydroid Google Pro toolkit."""
import os
import subprocess
import sys
import time
import datetime
import getpass
import json
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = os.environ.get("MTOOL_ROOT", "/srv/meowtools") + "/google-pro"
SAVED_STDIN = None
NULL_STDIN = None
MENU_IN = None
sys.path.insert(0, BASE)
os.environ.setdefault("ADB_PATH", os.path.join(BASE, "adb-waydroid"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("FRIDA_ARCH", "x86_64")

import ultra0
import vault_run
import oneclick as oc


def line():
    print("-" * 58, flush=True)


VAULT_DIR = Path(BASE) / ".vault"
VAULT_KEY = VAULT_DIR / "key.bin"
VAULT_DATA = VAULT_DIR / "accounts.enc"


def safe_load():
    try:
        return vault_run.load()
    except SystemExit:
        return []
    except Exception:
        return []


def vault_save(rows):
    VAULT_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not VAULT_KEY.exists():
        VAULT_KEY.write_bytes(AESGCM.generate_key(bit_length=256))
        os.chmod(VAULT_KEY, 0o600)
    os.chmod(VAULT_DIR, 0o700)
    nonce = os.urandom(12)
    ct = AESGCM(VAULT_KEY.read_bytes()).encrypt(nonce, json.dumps(rows).encode(), None)
    VAULT_DATA.write_bytes(nonce + ct)
    os.chmod(VAULT_DATA, 0o600)


def vault_clear():
    try:
        VAULT_DATA.unlink()
    except FileNotFoundError:
        pass
    print("Akun tersimpan di vault sudah dihapus.", flush=True)


def show_status():
    rows = safe_load()
    email = rows[-1]["email"] if rows else "-"
    print("EMAIL      :", email, flush=True)
    print("ACCOUNTS   :", oc.accounts(), flush=True)
    try:
        print("PLAY       :", ultra0.current_play_account(), flush=True)
    except Exception:
        print("PLAY       : -", flush=True)
    try:
        print("COUNTRY    :", oc.play_country(email), flush=True)
    except Exception:
        print("COUNTRY    : -", flush=True)
    try:
        ok, got, want = oc.check_billing_account(email)
        print("BILLING_OK :", ok, "GOT", got, flush=True)
    except Exception as e:
        print("BILLING_OK : ERROR", str(e)[:80], flush=True)
    try:
        price = oc.sku_price()
        print("SKU_MICROS :", price, "(IDR=309000000000)", flush=True)
    except Exception as e:
        print("SKU_MICROS : ERROR", str(e)[:80], flush=True)
    v = oc.lib_valid_until()
    print("SUB_UNTIL  :", datetime.datetime.fromtimestamp(v / 1000, datetime.timezone.utc).isoformat() if v else None, flush=True)


def ensure_google_one():
    if oc.ad("shell", "pm", "list", "packages").stdout.find(b"com.google.android.apps.subscriptions.red") >= 0:
        return True
    print("Google One belum terpasang — installing dari Play Store...", flush=True)
    oc.ad("shell", "am", "start", "-a", "android.intent.action.VIEW",
          "-d", "market://details?id=com.google.android.apps.subscriptions.red",
          "-p", "com.android.vending")
    time.sleep(8)
    xml = oc.dump("goinstall")
    b = oc.btn(xml, "Install")
    if not b:
        print("FAIL: tombol Install tidak ketemu", flush=True)
        return False
    oc.ad("shell", "input", "tap", str((b[0] + b[2]) // 2), str((b[1] + b[3]) // 2))
    for _ in range(24):
        time.sleep(5)
        if oc.ad("shell", "pm", "list", "packages").stdout.find(b"com.google.android.apps.subscriptions.red") >= 0:
            print("Google One terpasang.", flush=True)
            return True
    print("FAIL: Google One gagal install", flush=True)
    return False


def do_add_vault():
    global SAVED_STDIN, NULL_STDIN
    print("Menu 1: akun lama di vault dan di device akan dihapus dulu.", flush=True)
    vault_clear()
    do_clean()
    os.dup2(SAVED_STDIN, 0)
    try:
        subprocess.run(["/usr/bin/python3", os.path.join(BASE, "vault_add.py")])
    finally:
        os.dup2(NULL_STDIN, 0)
    rows = safe_load()
    print("Akun di vault:", [r["email"] for r in rows], flush=True)


def do_login():
    rows = safe_load()
    if not rows:
        print("Vault kosong. Pilih menu 1 dulu.", flush=True)
        return
    rec = rows[-1]
    print("Target:", rec["email"], flush=True)
    print("Menu 2: email/password diketik otomatis. Yang manual hanya CAPTCHA/2FA.", flush=True)
    oc.remote_help()
    for attempt in range(6):
        ok = oc.sign_in(rec["email"], rec.get("password", ""))
        if ok == "WRONG_PASSWORD":
            print("PASSWORD ANDA SALAH.", flush=True)
            try:
                newpw = getpass.getpass("Ketik ulang password untuk %s: " % rec["email"])
            except EOFError:
                newpw = ""
            if not newpw:
                print("Password kosong, login dibatalkan.", flush=True)
                return
            rec["password"] = newpw
            rows = [r for r in safe_load() if r.get("email") != rec["email"]]
            rows.append(rec)
            vault_save(rows)
            print("Password diperbarui di vault. Mencoba login lagi...", flush=True)
            continue
        if ok:
            print("LOGIN_RESULT: berhasil", flush=True)
            break
        print("LOGIN_RESULT: gagal, coba lagi (attempt %d)" % (attempt + 1), flush=True)
        try:
            again = input("Ulangi login? [y/N]: ").strip().lower()
        except EOFError:
            again = ""
        if not again.startswith("y"):
            break
    print("ACCOUNTS:", oc.accounts(), flush=True)


def do_claim(plan, stack):
    rows = safe_load()
    if not rows:
        print("Vault kosong. Pilih menu 1 dulu.", flush=True)
        return
    rec = rows[-1]
    ultra0.ADB = ultra0.find_adb()
    ultra0.SERIAL = oc.SERIAL
    if not ensure_google_one():
        return
    price = oc.sku_price()
    if price != 309000000000:
        print("FAIL: harga SKU", price, "bukan Rp 309.000. Klaim dibatalkan.", flush=True)
        print("Pastikan Play country + payment profile Indonesia.", flush=True)
        return
    print("Harga Rp 309.000 OK. Menjalankan", plan, flush=True)
    ok = oc.claim(plan, stack, rec.get("password", ""))
    print("CLAIM_RESULT:", ok, flush=True)
    print("SUBSCRIPTION:", show_subscription_text()[:900], flush=True)


def show_subscription_text():
    return " | ".join(dict.fromkeys(oc.texts(oc.dump("sub"))))


def do_clean():
    rows = safe_load()
    target = rows[-1]["email"] if rows else "__none__"
    print("Menghapus semua akun Google dari device...", flush=True)
    for acc in list(oc.accounts()):
        print("  hapus:", acc, flush=True)
    for _ in range(6):
        if not oc.accounts():
            break
        oc.remove_other_accounts("__none__")
    for pkg in ("com.google.android.gms", "com.android.vending",
                "com.google.android.googlequicksearchbox",
                "com.google.android.apps.subscriptions.red"):
        oc.ad("shell", "am", "force-stop", pkg)
        oc.ad("shell", "pm", "clear", pkg)
    oc.ad("shell", "rm", "-f", "/data/misc/adb/adb_keys")
    print("BERSIH. Device siap untuk akun baru.", flush=True)
    print("ACCOUNTS:", oc.accounts(), flush=True)


def menu():
    while True:
        line()
        print("MENU WAYDROID GOOGLE PRO", flush=True)
        print("1. Tambah akun ke vault (email/password)", flush=True)
        print("2. Login Google ke device (CAPTCHA/2FA manual)", flush=True)
        print("3. Claim step 1 - 12 bulan", flush=True)
        print("4. Claim step 2 - tambah 6 bulan", flush=True)
        print("5. Claim step 3 - tambah 6 bulan", flush=True)
        print("6. Cek status", flush=True)
        print("7. Bersihkan device (fresh untuk akun baru)", flush=True)
        print("8. Keluar", flush=True)
        print("9. Hapus akun tersimpan (vault + device)", flush=True)
        line()
        try:
            choice = input("Pilih [1-9]: ").strip()
        except EOFError:
            break
        if choice == "1":
            do_add_vault()
        elif choice == "2":
            do_login()
        elif choice == "3":
            do_claim("pro12", False)
        elif choice == "4":
            do_claim("pro6", True)
        elif choice == "5":
            do_claim("pro6b", True)
        elif choice == "6":
            show_status()
        elif choice == "7":
            do_clean()
        elif choice == "8":
            break
        elif choice == "9":
            vault_clear()
            do_clean()
        else:
            print("Pilihan nggak dikenal.", flush=True)
        time.sleep(1)


if __name__ == "__main__":
    SAVED_STDIN = os.dup(0)
    NULL_STDIN = os.open("/dev/null", os.O_RDONLY)
    MENU_IN = os.fdopen(SAVED_STDIN, "r")
    sys.stdin = MENU_IN
    os.dup2(NULL_STDIN, 0)
    # Pastikan runtime Waydroid/ADB siap sebelum masuk menu.
    try:
        subprocess.run([os.path.join(BASE, "start-runtime.sh")], timeout=300,
                       capture_output=True)
    except Exception as e:
        print("start-runtime gagal:", str(e)[:120], flush=True)
    try:
        subprocess.run(["/usr/bin/adb", "connect", oc.SERIAL],
                       capture_output=True, timeout=20)
    except Exception:
        pass
    ultra0.ADB = ultra0.find_adb()
    ultra0.pick_device()
    ultra0.SERIAL = oc.SERIAL
    menu()
