# PyManager

PyManager is a local desktop password manager for Windows. It encrypts vault
contents before writing them to disk and provides a graphical interface for
storing, searching, editing, and copying password entries.

## Features

- Encrypted local vault using AES-GCM and keys derived from the master password
  with Argon2id.
- Password generation with configurable lengths from 8 to 128 characters
  (20 characters by default).
- Search by service name or username.
- Clipboard clearing after 15 seconds when the clipboard still contains the
  copied password.
- Automatic vault lock after five minutes of inactivity.
- Responsive interface with scrollbars when the window is too small.

## Run the Windows executable

Download or copy `dist/release/PyManager.exe` to your Windows device and
double-click it. This is a portable executable, not an installer wizard.

On first launch, create a master password of at least 12 characters and enter
it again to confirm. There is no master-password recovery mechanism; keep the
master password safe.

The packaged app stores its encrypted vault at:

```text
%LOCALAPPDATA%\PyManager\my_vault.enc
```

Back up this file to a safe location to preserve your vault. Keep the backup
private, and do not share it together with your master password.

## Run from source

Install Python for Windows, then open Command Prompt in this directory and run:

```bat
py -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe gui.py
```

When running from source, `my_vault.enc` is created in the current working
directory.

## Build the executable

The build script installs the build dependencies, generates the Windows icon
from the bundled logo, and creates the standalone executable:

```bat
build_windows.bat
```

The output is `dist\release\PyManager.exe`. To build manually, install the
packages in `requirements-build.txt`, then run:

```bat
venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name PyManager --icon "assets\pymanager.ico" --add-data "assets\pymanager_logo.png;assets" --distpath "dist\release" --workpath "build\release" --specpath "build\spec" gui.py
```

## Create a Windows installer

Install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then build the app
executable and compile the installer:

```bat
build_windows.bat
build_installer.bat
```

The installer is written to
`dist\installer\PyManager-Setup-1.0.0.exe`. It installs per-user under
`%LOCALAPPDATA%\Programs\PyManager`, creates a Start Menu shortcut, and offers
an optional Desktop shortcut. It does not require administrator privileges.

The encrypted vault is stored separately under
`%LOCALAPPDATA%\PyManager\my_vault.enc`; uninstalling the app does not remove
the vault. Back up the vault file before uninstalling or moving to another
device.

## Project files

- `gui.py` — Tkinter desktop interface and application entry point.
- `vault.py` — Vault persistence and encrypted entry management.
- `crypto_utils.py` — Argon2id key derivation and AES-GCM encryption.
- `assets\pymanager_logo.png` — Application logo.
- `requirements.txt` — Runtime dependencies.
- `requirements-build.txt` — Runtime and executable-build dependencies.
- `build_windows.bat` — Windows executable build script.
- `installer\PyManager.iss` — Inno Setup installer definition.
- `build_installer.bat` — Windows installer build script.
