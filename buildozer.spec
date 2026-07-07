[app]

# (str) Title of your application
title = EarCare

# (str) Package name
package.name = earcare

# (str) Package domain (needed for android/ios packaging)
package.domain = org.earcare

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,ttf,otf,kv,atlas

# (list) List of inclusions using pattern matching
# Makes sure the Korean/Japanese font bundled in fonts/ gets packaged
source.include_patterns = fonts/*

# (str) Application versioning
version = 0.1

# (list) Application requirements
# python3 + kivy for the UI, numpy for the tone/audio math
requirements = python3,kivy,numpy

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
# This app only plays audio it generates itself -- no special permissions needed
android.permissions =

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (str) The Android arch to build for
android.archs = arm64-v8a,armeabi-v7a

# (int) overrides automatic versionCode computation
#android.numeric_version = 1

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
