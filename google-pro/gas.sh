#!/bin/bash
# Sekali klik: vault -> login -> hapus akun lama -> klaim 12 -> stack 6+6 -> verifikasi.
# Jalankan vault_add.py dulu sekali untuk menyimpan akun baru ke vault.
# Default: akun terakhir di vault. Ganti dengan: ./gas.sh --email nama@gmail.com
# Cek aman tanpa beli: ./gas.sh --check
set -e
BASE="${GOOGLE_PRO_DIR:-${MTOOL_ROOT:-/srv/meowtools}/google-pro}"
cd "$BASE"
exec /usr/bin/python3 "$BASE/oneclick.py" "$@"
