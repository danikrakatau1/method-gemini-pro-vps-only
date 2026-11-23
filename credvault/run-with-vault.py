#!/usr/bin/env python3
"""Run ultra0.py with a credential from the encrypted vault.

Secrets are passed only through environment variables to the child process;
they are never placed in argv and never written to a file.
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.environ.get("CREDVAULT_DIR", "/srv/meowtools/credvault"))
from credvault import load_key, load_vault  # noqa: E402

ULTRA = os.environ.get("ULTRA0_PATH", "/srv/meowtools/google-pro/ultra0.py")
PYTHON = "/usr/bin/python3"


def main():
    ap = argparse.ArgumentParser(description="run Google-Pro toolkit with vaulted credential")
    ap.add_argument("name", help="credential name in vault")
    ap.add_argument("extra", nargs=argparse.REMAINDER)
    a = ap.parse_args()

    key = load_key()
    vault = load_vault(key)
    if a.name not in vault:
        raise SystemExit(f"credential not found: {a.name}")
    rec = vault[a.name]

    env = os.environ.copy()
    env.update({
        "ADB_PATH": os.environ.get("ADB_WRAPPER", "/srv/meowtools/google-pro/adb-waydroid"),
        "PYTHONIOENCODING": "utf-8",
        "FRIDA_ARCH": "x86_64",
        "CRED_EMAIL": rec.get("email", ""),
        "CRED_PASSWORD": rec.get("password", ""),
        "CRED_TOTP": rec.get("totp", ""),
        "CRED_RECOVERY": rec.get("recovery", ""),
        "CRED_CARD_NUMBER": rec.get("card_number", ""),
        "CRED_CARD_EXP": rec.get("card_exp", ""),
        "CRED_CARD_CVC": rec.get("card_cvc", ""),
        "CRED_CARD_HOLDER": rec.get("card_holder", ""),
        "CRED_CARD_ZIP": rec.get("card_zip", ""),
    })

    extra = list(a.extra)
    if extra and extra[0] == "--":
        extra = extra[1:]
    cmd = [PYTHON, ULTRA, "--account-env"] + extra
    try:
        return subprocess.call(cmd, env=env, cwd=os.environ.get("GOOGLE_PRO_DIR", "/srv/meowtools/google-pro"))
    finally:
        for k in list(env):
            if k.startswith("CRED_"):
                env.pop(k, None)


if __name__ == "__main__":
    sys.exit(main())
