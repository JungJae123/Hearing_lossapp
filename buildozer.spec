[app]

# (str) Title of your application
title = EarCare

# (str) Package name
package.name = earcare

# (str) Package domain (needed for android/ios packaging)
package.domain = org.jungjae

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,ttf

# (str) Application versioning (method 1)
version = 1.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.3.0,numpy

# (list) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (int) Android NDK API to use.
android.ndk_api = 21

# (bool) automatically accept SDK license agreements (needed for CI)
android.accept_sdk_license = True

# (str) The Android arch to build for.
# Single arch keeps the CI build fast and reliable. arm64-v8a covers
# essentially all modern Android phones.
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
