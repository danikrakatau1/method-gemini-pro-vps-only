#!/usr/bin/env python3
"""Drive Waydroid input using secrets from the encrypted vault.

The agent can ask for a field to be typed without ever seeing the plaintext.
"""
import argparse
import shlex
import subprocess
import sys

sys.path.insert(0, os.environ.get("CREDVAULT_DIR", "/srv/meowtools/credvault"))
from credvault import load_key, load_vault  # noqa: E402

ADB = "/usr/bin/adb"


def adb(*args):
    subprocess.run([ADB, *args], check=True)


def android_text(text):
    # Android `input text` uses %s for a literal space.
    escaped = str(text).replace(" ", "%s")
    return shlex.quote(escaped)


def main():
    ap = argparse.ArgumentParser(description="type vaulted credentials into Waydroid via ADB")
    ap.add_argument("name")
    ap.add_argument("action", choices=["email", "password", "totp", "tap", "keyevent"])
    ap.add_argument("value", nargs="*", default=[])
    a = ap.parse_args()

    key = load_key()
    vault = load_vault(key)
    if a.name not in vault:
        raise SystemExit(f"credential not found: {a.name}")
    rec = vault[a.name]

    mapping = {
        "email": rec.get("email", ""),
        "password": rec.get("password", ""),
        "totp": rec.get("totp", ""),
    }

    if a.action in mapping:
        if not mapping[a.action]:
            raise SystemExit(f"field {a.action} is empty")
        adb("shell", "input", "text", android_text(mapping[a.action]))
        print(f"typed {a.action} from vault")
        return 0

    if a.action == "tap":
        vals = list(a.value)
        if len(vals) < 2:
            raise SystemExit("tap needs X Y")
        adb("shell", "input", "tap", vals[0], vals[1])
        print("tapped")
        return 0

    if a.action == "keyevent":
        if not a.value:
            raise SystemExit("keyevent needs KEYCODE")
        adb("shell", "input", "keyevent", a.value[0])
        print("keyevent sent")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
