# Goodwill Scanner

Android document scanner for the Redmi 13C (Android 7.0 and above).

## Features
- Camera scan with automatic edge detection, crop, straightening and auto-capture (Google ML Kit).
- Import from the gallery.
- Book mode: a landscape photo of an open book is split into left and right pages.
- Page filters: Original, Magic colour, Greyscale, B & W (shadow removal).
- Rotate, reorder and delete pages.
- Text extraction (English / Latin script), copy or share.
- Export as PDF, JPG images or text; save PDF to the phone.
- Folders.

## Install on the phone
1. Open the repository's **Releases** page on the phone and download the latest `GoodwillScanner.apk`.
2. Open it and allow "Install unknown apps" for the browser or file manager when asked.
3. On first scan, Google Play services downloads the scanner module (needs internet once).

## Build
`./gradlew assembleRelease` (needs the Android SDK). GitHub Actions builds it on every push.
