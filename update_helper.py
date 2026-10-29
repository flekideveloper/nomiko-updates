"""Separate Windows updater process. Waits for NOMIKO to exit before running NSIS."""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def wait_for_pid(pid: int, seconds: int = 120) -> bool:
    if os.name != 'nt':
        return False
    SYNCHRONIZE = 0x00100000
    WAIT_OBJECT_0 = 0
    WAIT_TIMEOUT = 258
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.argtypes = [ctypes.wintypes.DWORD, ctypes.wintypes.BOOL, ctypes.wintypes.DWORD]
    kernel.OpenProcess.restype = ctypes.wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
    kernel.WaitForSingleObject.restype = ctypes.wintypes.DWORD
    kernel.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    handle = kernel.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return True  # process already exited
    try:
        return kernel.WaitForSingleObject(handle, seconds * 1000) == WAIT_OBJECT_0
    finally:
        kernel.CloseHandle(handle)


def installer_is_safe(path: Path, checksum: str) -> bool:
    if not re.fullmatch('[a-f0-9]{64}', checksum):
        return False
    local = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    allowed = (Path(local) / 'NOMIKO' / 'updates').resolve()
    p = path.resolve()
    if p.parent != allowed or not re.fullmatch(r'NOMIKO-Setup-\d+\.\d+\.\d+(?:-alpha|-beta|-rc)?\.exe', p.name):
        return False
    if not p.is_file():
        return False
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest() == checksum


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--installer', required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    if args.pid <= 0 or not installer_is_safe(Path(args.installer), args.sha256):
        return 3
    if not wait_for_pid(args.pid):
        return 4
    # Allow Windows to release any loaded app DLLs before NSIS replaces them.
    time.sleep(2)
    if not installer_is_safe(Path(args.installer), args.sha256):
        return 5
    proc = subprocess.run([str(Path(args.installer)), '/S'], timeout=180, check=False)
    return proc.returncode


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        sys.exit(10)
