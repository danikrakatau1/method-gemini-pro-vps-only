# One-click 12 + 6 + 6 month flow

This documents the `gas.sh` runner that was validated end-to-end on Waydroid.

## Sanitized public repo

The repo contains code only. No vault keys, encrypted vault files, passwords,
purchase tokens, real account emails, VPS IPs, domains, or tailnet identities.

## Quick start on a fresh VPS

```bash
git clone <REPO_URL> waydroid-toolkit
cd waydroid-toolkit
sudo ./install.sh
/srv/meowtools/google-pro/start-runtime.sh
/usr/bin/python3 /srv/meowtools/google-pro/vault_add.py
/srv/meowtools/google-pro/gas.sh --check
/srv/meowtools/google-pro/gas.sh
```

`gas.sh --check` is read-only: it prints the account, Play country, billing
account hash, SKU price, and current subscription without buying anything.
The real run adds the vault account, removes old Google accounts from the
device, switches Play Store, verifies the SKU price, then claims 12 months
and stacks 6 + 6 months. CAPTCHA and 2FA are handed to the account owner.

## Why the price check matters

Google Play serves a region-specific price. An ID payment profile gives
`309000000000` micros (Rp 309.000); a US/SG profile gives `19990000`
($19.99) and the trial can be rejected with
`The item you requested is not available for purchase`. `gas.sh` stops
when the price is not IDR, so no unintended charge is made.

## Billing account gotcha

`Billing preferred account via installer` in logcat carries
`base64url(SHA256(account_email))`. Removing the old Google account from the
device is what rebinds billing to the remaining account; changing the Play
Store UI account, reinstalling the app, or clearing Play Store data alone
is not enough. `gas.sh` performs the removal automatically.

## Credentials

`vault_add.py` reads email/password/TOTP/card data with `getpass` and writes
an AES-GCM encrypted file with a 0600 key generated locally on the target
VPS. Secrets are never passed in argv, written to logs, or committed.
