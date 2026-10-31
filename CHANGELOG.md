# NOMIKO changelog

## v0.9.1 Alpha
- Graphite NOMIKO Windows icon (16px to 256px).
- EXE and taskbar icon + stable AppUserModelID.
- Desktop and Start Menu shortcuts with branded icons, removed on uninstall.
- Signed GitHub Alpha release pipeline and existing Update Center integration.
- All browser settings stay in %APPDATA%\NOMIKO.

# NOMIKO v0.9.0 Alpha — Update foundation

- Added signed update discovery via GitHub Releases API (Ed25519 pinned public key).
- Installer download verifies signed size and SHA-256, rejects suspicious filenames and mismatched tags.
- Added Update Center UI and Settings → Updates; default launch check can be disabled.
- Added external Windows update helper that waits for NOMIKO to exit before running NSIS silently after user confirmation.
- GitHub Actions builds Windows portable EXE, helper, NSIS setup, and signs releases with a repository secret.
- Local user profile data lives separately from app install files.
- Added offline updater tests.

**Deployment incomplete:** repository, Actions signing secret, first GitHub release and live Windows checks still required. Windows Authenticode signing, rollback and delta patching are not implemented.

---

# NOMIKO changelog

## v0.8.2 Alpha (Windows 11)

Fixed vertical tab reordering in both left/right sidebars. Replaced the incompatible native QTabBar sidebar drag with pointer-following paint, animated neighbor shifts and a real moveTab drop. Works with favicon-only and expanded titles. Close controls cannot accidentally trigger while dragging. Background tabs do not activate during drag. No changes to web engine or user data. 55 offline tests pass; Windows 11 GUI interaction still needs verification.

## v0.8.1 Alpha (Windows 11)

Fixed Split View: independent searches on left/right, independent DuckDuckGo / Google / local NOMIKO Search selectors, working Enter/search buttons and navigation controls. Right pane starts on local NOMIKO home instead of requiring a URL prompt. Existing web security/navigation interceptors are shared by split panes. Ctrl+L, back/forward/reload/home, bookmarks and find-in-page target active pane. 49 offline tests pass, GUI not yet verified on Windows 11.

## v0.8.0 Alpha (Windows 11)

New tab tools: pin/unpin, named group tags, Ctrl+Shift+A switcher, named local workspaces, Split View tab, HTML-to-text reader, experimental website PiP request.

New local data tools: HTML bookmark migration, secure ZIP allowlisted backups with safeguards against zip path traversal and backup snapshots, Windows DPAPI encrypted manual password notes (without form autofill).

Appearance and modules: six theme presets, theme JSON import/export with validation, live interface font scale, opt-in local domain-blocking file (no executable extensions).

Safety/performance: HTTP and Punycode warning prompts, executable-download warnings, user-control permissions view, performance monitor showing process-only RAM. Existing background tab management retained.

Developer build: Windows PyInstaller script, GitHub Actions workflow and NSIS installer source. No Windows binary compiled during this update.

44 offline tests pass. No Qt/Windows GUI test has been performed in this environment.

Remaining goals: audited security and anonymity; signed update distribution; robust phishing/malware intelligence; WebExtensions or a security-reviewed plugin SDK; password autofill and a stronger vault architecture; complete localization; comprehensive usability and Windows integration tests.

Earlier changes from v0.7.2 remain in the source history / prior release changelog.
