#!/usr/bin/env python3
"""Encrypted local credential vault for sg-main.

Secrets never need to be pasted into chat. The vault is encrypted with AES-GCM
using a 32-byte key file stored with mode 0600 on the VPS. Use `add` interactively
so passwords are read with getpass and never appear in shell history or argv.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = Path(os.environ.get("CREDVAULT_DIR", "/srv/meowtools/credvault"))
KEY_FILE = BASE / "key.bin"
VAULT_FILE = BASE / "vault.enc"
AAD = b"credvault-v1"

FIELDS = [
    "email", "password", "recovery", "totp",
    "card_number", "card_exp", "card_cvc", "card_holder", "card_zip",
]


def ensure_base():
    BASE.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(BASE, 0o700)


def init_key(force=False):
    ensure_base()
    if KEY_FILE.exists() and not force:
        print(f"key already exists: {KEY_FILE}")
        return
    KEY_FILE.write_bytes(os.urandom(32))
    os.chmod(KEY_FILE, 0o600)
    print(f"key created: {KEY_FILE} (mode 0600)")


def load_key():
    if not KEY_FILE.exists():
        raise SystemExit(f"key missing; run: {sys.argv[0]} init-key")
    key = KEY_FILE.read_bytes()
    if len(key) != 32:
        raise SystemExit("key file must be exactly 32 bytes")
    return key


def load_vault(key):
    if not VAULT_FILE.exists():
        return {}
    blob = json.loads(VAULT_FILE.read_text(encoding="utf-8"))
    nonce = base64.b64decode(blob["nonce"])
    ct = base64.b64decode(blob["ct"])
    plain = AESGCM(key).decrypt(nonce, ct, AAD)
    return json.loads(plain.decode("utf-8"))


def save_vault(key, data):
    ensure_base()
    nonce = os.urandom(12)
    plain = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ct = AESGCM(key).encrypt(nonce, plain, AAD)
    blob = {
        "version": 1,
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ct": base64.b64encode(ct).decode("ascii"),
    }
    tmp = VAULT_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(blob), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, VAULT_FILE)
    os.chmod(VAULT_FILE, 0o600)


def add_credential(name, values):
    key = load_key()
    vault = load_vault(key)
    clean = {k: str(values.get(k, "") or "") for k in FIELDS}
    vault[name] = clean
    save_vault(key, vault)
    print(f"credential saved: {name}")


def mask_email(email):
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    head = local[:2] if len(local) > 2 else local[:1]
    return f"{head}***@{domain}"


def main():
    ap = argparse.ArgumentParser(description="encrypted credential vault")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-key", help="create 0600 master key file")
    sub.add_parser("list", help="list credential names with masked emails")

    p_add = sub.add_parser("add", help="interactively add/update a credential")
    p_add.add_argument("name")
    p_add.add_argument("--email")
    p_add.add_argument("--recovery")
    p_add.add_argument("--totp")
    p_add.add_argument("--card-exp")
    p_add.add_argument("--card-holder")
    p_add.add_argument("--card-zip")

    p_get = sub.add_parser("get", help="output one credential as JSON")
    p_get.add_argument("name")

    p_rm = sub.add_parser("remove", help="delete a credential")
    p_rm.add_argument("name")

    p_run = sub.add_parser("run", help="run a command with CRED_* env vars set")
    p_run.add_argument("name")
    p_run.add_argument("command", nargs=argparse.REMAINDER)

    a = ap.parse_args()

    if a.cmd == "init-key":
        init_key()
        return 0

    key = load_key()
    vault = load_vault(key)

    if a.cmd == "list":
        if not vault:
            print("(empty)")
        for name, rec in sorted(vault.items()):
            print(f"{name}\t{mask_email(rec.get('email',''))}")
        return 0

    if a.cmd == "add":
        rec = {}
        rec["email"] = a.email if a.email is not None else input("email: ").strip()
        import getpass
        rec["password"] = getpass.getpass("password: ")
        rec["recovery"] = a.recovery if a.recovery is not None else input("recovery (optional): ").strip()
        rec["totp"] = a.totp if a.totp is not None else input("totp seed/code (optional): ").strip()
        use_card = input("add card details? [y/N]: ").strip().lower().startswith("y")
        if use_card:
            rec["card_number"] = getpass.getpass("card number: ")
            rec["card_exp"] = a.card_exp if a.card_exp is not None else input("exp (MM/YY): ").strip()
            rec["card_cvc"] = getpass.getpass("CVC: ")
            rec["card_holder"] = a.card_holder if a.card_holder is not None else input("holder: ").strip()
            rec["card_zip"] = a.card_zip if a.card_zip is not None else input("zip: ").strip()
        add_credential(a.name, rec)
        return 0

    if a.cmd == "get":
        if a.name not in vault:
            raise SystemExit(f"credential not found: {a.name}")
        print(json.dumps(vault[a.name], ensure_ascii=False))
        return 0

    if a.cmd == "remove":
        if a.name not in vault:
            raise SystemExit(f"credential not found: {a.name}")
        del vault[a.name]
        save_vault(key, vault)
        print(f"credential removed: {a.name}")
        return 0

    if a.cmd == "run":
        if a.name not in vault:
            raise SystemExit(f"credential not found: {a.name}")
        if not a.command:
            raise SystemExit("run needs a command after the credential name")
        rec = vault[a.name]
        env = os.environ.copy()
        env.update({
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
        cmd = list(a.command)
        if cmd and cmd[0] == "--":
            cmd = cmd[1:]
        try:
            return subprocess.call(cmd, env=env)
        finally:
            for k in list(env):
                if k.startswith("CRED_"):
                    env.pop(k, None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
