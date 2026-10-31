# NOMIKO browser — official releases

Windows 11 browser source and build pipeline. v0.9.1 Alpha adds a multi-size graphite NOMIKO icon, desktop and Start shortcuts, and taskbar identity.

## Real update flow
- Windows Actions builds NOMIKO.exe, the update helper, and NSIS setup; runs offline tests.
- An explicit release request (.github/release-request.txt) triggers signing and GitHub Releases publication after a successful Windows build.
- The existing GitHub Actions secret NOMIKO_SIGNING_KEY_B64 signs update.json; the browser pins the matching public Ed25519 key.
- The Update Center verifies Ed25519 signature and installer SHA-256, then installs only after user confirmation and browser shutdown.
- Browser data in %APPDATA%\NOMIKO is preserved by uninstall and update.

This is an experimental alpha; Windows Authenticode signing and full GUI regression testing are separate tasks.
