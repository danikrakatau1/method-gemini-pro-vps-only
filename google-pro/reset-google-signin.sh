#!/bin/bash
# Reset Google Play Services / Play Store sign-in state in Waydroid.
set -e
ADB=/usr/bin/adb
$ADB shell am force-stop com.google.android.gms >/dev/null 2>&1 || true
$ADB shell am force-stop com.google.android.gms.ui >/dev/null 2>&1 || true
$ADB shell am force-stop com.android.vending >/dev/null 2>&1 || true
$ADB shell pm clear com.google.android.gms >/dev/null 2>&1 || true
$ADB shell pm clear com.google.android.gms.ui >/dev/null 2>&1 || true
$ADB shell pm clear com.android.vending >/dev/null 2>&1 || true
$ADB shell pm clear com.google.android.googlequicksearchbox >/dev/null 2>&1 || true
sleep 2
$ADB shell monkey -p com.android.vending -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
echo "google sign-in state reset; Play Store dibuka"
