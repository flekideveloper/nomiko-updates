# NOMIKO — official updates

Official public Windows release repository for **NOMIKO**, an independent privacy-focused browser.

**Status:** Repository bootstrap. The signed update workflow is prepared but the full NOMIKO v0.9.0 source code, a Windows-tested EXE, and the first signed release are **not yet published**.

## Build and release plan

1. Upload the **contents** of the `NOMIKO-Windows11` directory from `NOMIKO-Windows11-v0.9.0-update-system.zip` into the root of this repository. Preserve folder structure, including `src/`, `tests/`, `installer/`, and `tools/`. Keep the existing GitHub Actions workflow unless intentionally updating it.
2. Add the GitHub Actions repository secret named `NOMIKO_SIGNING_KEY_B64` using the privately saved signing key. **Never commit this key.**
3. Open **Actions → NOMIKO Windows build and signed release → Run workflow** on `main` to produce a **test build**. This does not publish a release.
4. Download the build artifact and manually test installation, app start, browsing, downloads, uninstallation and preservation of user data on Windows 11.
5. Only after that smoke test passes, create and push the tag `v0.9.0-alpha` pointing at the tested commit. The workflow signs `update.json` with Ed25519, verifies the pinned public key and publishes the installer and portable ZIP to GitHub Releases.
6. To test an actual **update**, prepare and release a new version (for example `v0.9.1-alpha`) with matching version constants, signed manifest, and build settings. A v0.9.0 browser will not offer v0.9.0 as an update.

## Security

- The public key may be committed; the **private Ed25519 signing key must only be held offline and added to GitHub Actions Secrets**.
- A release must pass signature and SHA-256 verification before installation. Downloading from GitHub alone is insufficient.
- Microsoft Windows Authenticode code signing is **not included**. SmartScreen may warn that the publisher is unknown.
- Browser data resides under `%APPDATA%\NOMIKO` and must not be added to the repository or releases.
- Do not claim live automatic updates until the first signed release and the updater have been tested on Windows 11.

## Project

Windows 11 / Python / PySide6 / Qt WebEngine. NOMIKO is independent from AURVEX.

*This repository hosts browser releases, not personal browsing data.*
