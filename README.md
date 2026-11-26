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

Untuk VPS dengan Tailscale:

```bash
sudo TAILSCALE_IP=100.x.y.z ./install.sh
```

Untuk VPS dengan domain:

```bash
sudo DOMAIN=contoh.com ./install.sh
```

Installer melakukan:
- install paket Waydroid, LXC, Weston, ADB, socat, Flask, Frida, dan bcrypt
- daftarkan repo Waydroid
- siapkan `/dev/binderfs` dan override systemd
- generate kunci vault dan kunci sesi panel
- generate password remote di `waydroid-web/password.txt` dengan izin `600`
- unduh frida-server x86_64
- init image Waydroid GAPPS jika belum ada
- pasang panel remote lokal di `127.0.0.1:8765`
- pasang panel antrean di `127.0.0.1:8766` atau di IP Tailscale
- buat unit systemd `waydroid-remote` dan `gemini-queue`
- buat `Caddyfile.generated` jika `DOMAIN` diisi

## Setelah install

Jalankan menu utama:

```bash
/srv/meowtools/gas.sh
```

Menu:
1. Tambah akun ke vault
2. Login Google ke device (CAPTCHA/2FA manual lewat web remote)
3. Claim 12 bulan
4. Claim tambah 6 bulan (step 2)
5. Claim tambah 6 bulan (step 3)
6. Cek status
7. Bersihkan device (fresh untuk akun baru)
8. Keluar
9. Hapus akun tersimpan (vault + device)

Untuk pakai lama: `gas.sh` → pilih 7 → mulai lagi dari menu 1.

Cara manual (opsional):

```bash
/srv/meowtools/credvault/vault add akun1
/srv/meowtools/google-pro/start-runtime.sh
/srv/meowtools/google-pro/0_cek.sh
```

Setelah install, buka panel antrean:

- Tanpa domain: `http://127.0.0.1:8766/geminitoddd2tahun/`
- Dengan Tailscale: `http://<IP-TAILSCALE>:8766/geminitoddd2tahun/`
- Dengan domain: `https://<DOMAIN>/geminitoddd2tahun/`

Daftar akun web di `/geminitoddd2tahun/register`, lalu login. Akun web bukan akun
Google. Password web hanya disimpan sebagai hash bcrypt.

Login ke Google di Play Store Waydroid secara manual. Selesaikan CAPTCHA dan 2FA
sendiri. Kata sandi Google tidak pernah disimpan dan tidak pernah dikirim ke chat.

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

Atau pakai runner sekali klik (12 + 6 + 6 bulan) — lihat `ONECLICK.md`:

```bash
/srv/meowtools/google-pro/gas.sh --check   # aman, tidak membeli
/srv/meowtools/google-pro/gas.sh           # jalankan klaim
```

## Remote panel

Panel remote berjalan di `127.0.0.1:8765`. Jangan expose langsung ke internet.
Pakai reverse proxy dengan autentikasi. Contoh Caddy ada di `Caddyfile.example`.

### Tanpa domain

Domain tidak wajib untuk menyelesaikan CAPTCHA. CAPTCHA ada di layar Android,
bukan di domain. Panel web cuma mengantar screenshot dan tap.

Tanpa domain, pilihannya:

- Akses lewat Tailscale: buka `http://<IP-TAILSCALE>:8765/waydroid/remote`.
  Traffic sudah terenkripsi oleh Tailscale, jadi HTTPS tidak diperlukan.
- SSH tunnel dari HP/Termux: `ssh -L 8765:127.0.0.1:8765 user@VPS`, lalu buka
  `http://127.0.0.1:8765/waydroid/remote` di browser HP.
- Tanpa web sama sekali: pakai ADB relay Tailscale, tarik screenshot dengan
  `adb exec-out screencap -p`, lalu kirim `input tap`, `input text`, dan `input keyevent`.

Domain + HTTPS + basicauth hanya diperlukan kalau panel mau diakses publik
lewat internet biasa.

## Batasan

- Satu Waydroid instance hanya satu Android user aktif.
- Satu VPS realistisnya muat 2-3 instance aktif.
- Banyak user aktif bersamaan memerlukan antrean, VPS tambahan, atau lebih RAM.
- Tidak bisa dijalankan langsung di Termux/HP non-root sebagai engine.
- Google dapat meminta verifikasi kapan saja; itu tetap manual.

## Dipakai banyak orang

Tiap orang pakai VPS-nya sendiri dan vaultnya sendiri. Tidak ada kredensial bersama.

Syarat tiap VPS:
- x86_64, virtualisasi KVM, cgroup v2, `CONFIG_MEMFD_CREATE=y`
- minimal 2 vCPU / 4 GB RAM
- akses root
- HP Indonesia untuk verifikasi Google (CAPTCHA/2FA)
- akun Google dengan profil pembayaran Indonesia jika mau harga Rp 309.000

Semua path bisa diubah lewat environment tanpa edit script:

```
export MTOOL_ROOT=/srv/meowtools        # default
export SCRATCH_DIR=$HOME/.hermes/cache/scratch  # default
```

Alur untuk tiap orang:

```
git clone https://github.com/danikrakatau1/method-gemini-pro-vps-only.git waydroid-toolkit
cd waydroid-toolkit && ./install.sh
/srv/meowtools/gas.sh
```

Lalu pilih menu 1 (tambah akun), 2 (login), 6 (cek), 3/4/5 (klaim), 7/9 (bersih).

## Biar awet (anti-flag)

- Menu 1 **tidak lagi menghapus** vault/akun otomatis. Akun lama tetap dipakai. Kalau mau bersih, pakai menu 7 atau 9.
- Menu 2 **skip sign-in** kalau akun sudah ada di device.
- Menu 2 maksimal **2 attempt**, lalu aktifkan cooldown otomatis.
- Cooldown default 30 menit setelah gagal, atau **72 jam** kalau Google menyebut recovery / couldn't verify.
- Menu 3/4/5 menolak klaim kalau akun belum login — nggak memaksa login.

Environment:

```
LOGIN_COOLDOWN=1800              # detik, default 30 menit
LOGIN_COOLDOWN_LONG=259200       # detik, default 72 jam
FORCE_LOGIN=1                    # lewati cooldown (hati-hati)
AUTO_CLEAN_ON_ADD=1              # kembalikan perilaku lama menu 1 (auto-clear)
```

Aturan emas: sekali akun masuk, **jangan dihapus/clear lagi**. Pakai menu 6 → 3/4/5 sepuasnya.

## Ekstensi Chrome — mode Pro runtime

Folder `ultra inject` sekarang punya preset **AI Pro 12 / +6 / +6b** yang nggak pakai token statis:

- `inject.js` memantau respons XHR/fetch dan menyimpan token `AYrTWi...` yang dikirim Google saat checkout dimuat.
- Kalau belum ada token, preset **probe**: request diubah ke SKU `g1.2tb.ai.subs_variant` + offer `12months-eft` / `6months-eft` / `6months-eft-2`, lalu token diambil dari respons Google.
- Token hasil tangkapan disimpan di `chrome.storage.local` (`g1CapturedTokens`) dan dipakai ulang.
- Preset lama (20TB/30TB) tetap pakai token bawaan.

Cara pakai:
1. Load unpacked folder `ultra inject` di `chrome://extensions`
2. Login Google One di Chrome dengan akun yang eligible
3. Buka `one.google.com/plans`, pilih preset **AI Pro**
4. Tunggu status "Token Google terdeteksi", lalu klik Subscribe
5. Price guard harus hijau ($0.00 / free trial)

Catatan: Google tetap yang menentukan apakah offer diberikan. Kalau akun tidak eligible, tidak ada token untuk ditangkap.

## Privasi

Jangan pernah commit:
- `key.bin`
- `secret.key`
- `vault.enc`
- `password.txt`
- `hash.txt`
- `ultra0-report/`
- token purchase atau data akun

Meow.
