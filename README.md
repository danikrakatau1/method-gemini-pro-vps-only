# Waydroid Toolkit - sanitized public repo

Toolkit otomatis berbasis Waydroid + ADB + Frida untuk lingkungan VPS Linux.
Repo ini hanya berisi kode dan konfigurasi. Tidak ada kunci, kata sandi, token,
atau akun Google di sini.

## Yang dibutuhkan

- VPS Linux x86_64, Ubuntu/Debian, akses root
- Kernel dengan dukungan binder/binderfs, cgroup v2, dan overlay
- 2-4 vCPU, 6-8 GB RAM, 30-40 GB disk
- Internet keluar untuk apt, GitHub, OTA Waydroid, dan PyPI
- Tailscale/WireGuard jika ingin kontrol dari HP tanpa port publik
- Akun Google sendiri dan metode pembayaran sendiri

## Install

```bash
git clone <REPO_URL> waydroid-toolkit
cd waydroid-toolkit
sudo ./install.sh
```

Installer melakukan:
- install paket Waydroid, LXC, Weston, ADB, socat, Flask, Frida
- daftarkan repo Waydroid
- siapkan `/dev/binderfs` dan override systemd
- generate kunci vault lokal
- unduh frida-server x86_64
- init image Waydroid GAPPS jika belum ada
- aktifkan panel remote lokal di `127.0.0.1:8765`

## Setelah install

```bash
/srv/meowtools/credvault/vault add akun1
/srv/meowtools/google-pro/start-runtime.sh
/srv/meowtools/google-pro/0_cek.sh
```

Login ke Google di Play Store Waydroid secara manual. Selesaikan CAPTCHA dan 2FA
sendiri. Kata sandi tidak pernah disimpan dan tidak pernah dikirim ke chat.

## Jalankan alur

```bash
/srv/meowtools/google-pro/1_list.sh
/srv/meowtools/google-pro/2_pro12_langkah1.sh
/srv/meowtools/google-pro/3_pro6_langkah2.sh
/srv/meowtools/google-pro/4_pro6_langkah3.sh
```

Atau dengan vault:

```bash
/srv/meowtools/credvault/vault-run akun1 -- --force --no-add --stack --plan pro6
```

## Remote panel

Panel remote berjalan di `127.0.0.1:8765`. Jangan expose langsung ke internet.
Pakai reverse proxy dengan autentikasi. Contoh Caddy ada di `Caddyfile.example`.

## Batasan

- Satu Waydroid instance hanya satu Android user aktif.
- Satu VPS realistisnya muat 2-3 instance aktif.
- Banyak user aktif bersamaan memerlukan antrean, VPS tambahan, atau lebih RAM.
- Tidak bisa dijalankan langsung di Termux/HP non-root sebagai engine.
- Google dapat meminta verifikasi kapan saja; itu tetap manual.

## Privasi

Jangan pernah commit:
- `key.bin`
- `vault.enc`
- `password.txt`
- `hash.txt`
- `ultra0-report/`
- token purchase atau data akun

Meow.
