[app]
title = Sistema Ventas PRO
package.name = sistemaventas
package.domain = com.xervitec.sistemaventas

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2

# Android
[app:android]
# version 33 = Android 13 compatible
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license_agreement = True
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,CAMERA
android.application = android

# Icono si tienes uno
#icon.filename = %(source.dir)s/icon.png
