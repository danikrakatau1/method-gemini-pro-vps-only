#!/usr/bin/env python3
"""Simpan kredensial akun Google ke vault terenkripsi lokal (AES-GCM).

Jalankan di terminal sendiri. Semua rahasia dibaca dengan getpass,
tidak pernah diketik di chat, tidak masuk argv, tidak masuk log.
"""
import base64
import getpass
import json
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VAULT = Path(os.environ.get("MTOOL_ROOT", "/srv/meowtools")) / "google-pro" / ".vault"
KEY = VAULT / "key.bin"
DATA = VAULT / "accounts.enc"


def load() -> list:
    if not DATA.exists():
        return []
    blob = DATA.read_bytes()
    key = KEY.read_bytes()
    return json.loads(AESGCM(key).decrypt(blob[:12], blob[12:], None))


def save(rows: list) -> None:
    VAULT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not KEY.exists():
        KEY.write_bytes(AESGCM.generate_key(bit_length=256))
        os.chmod(KEY, 0o600)
    os.chmod(VAULT, 0o700)
    nonce = os.urandom(12)
    blob = nonce + AESGCM(KEY.read_bytes()).encrypt(nonce, json.dumps(rows).encode(), None)
    DATA.write_bytes(blob)
    os.chmod(DATA, 0o600)


def main() -> int:
    print("Vault kredensial lokal - input disembunyikan (getpass).")
    email = input("Email Google: ").strip()
    if not email:
        print("Email kosong, batal.")
        return 1
    password = getpass.getpass("Password Google: ")
    totp = getpass.getpass("TOTP/2FA seed (kosongkan kalau tidak ada): ").strip()
    print("Kartu pembayaran (kosongkan kalau kartu sudah tersimpan di akun Google):")
    number = getpass.getpass("Nomor kartu: ").strip()
    exp = input("Exp (MM/YY): ").strip() if number else ""
    cvc = getpass.getpass("CVC: ").strip() if number else ""
    holder = input("Nama pemilik kartu: ").strip() if number else ""
    zipp = input("Kode pos billing (contoh Indonesia 40171): ").strip() if number else ""

    rec = {
        "email": email,
        "password": password,
        "totp": totp,
        "card": {"number": number, "exp": exp, "cvc": cvc, "holder": holder, "zip": zipp},
    }
    rows = [r for r in load() if r.get("email") != email]
    rows.append(rec)
    save(rows)
    print(f"Tersimpan: {email} ({len(rows)} akun di vault). Rahasia tidak ditampilkan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
