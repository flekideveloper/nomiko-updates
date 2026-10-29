"""Windows-only, per-user DPAPI protected password notes. No network / no autofill."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path


class _BLOB(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_byte))]


def _crypt(data: bytes, encrypt: bool) -> bytes:
    if os.name != 'nt':
        raise RuntimeError('The local password vault requires Windows DPAPI')
    crypto = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    protect = crypto.CryptProtectData if encrypt else crypto.CryptUnprotectData
    protect.restype = wintypes.BOOL
    # Keep C-compatible input buffer alive while the WinAPI call runs.
    inbuf = ctypes.create_string_buffer(data)
    incoming = _BLOB(len(data), ctypes.cast(inbuf, ctypes.POINTER(ctypes.c_byte)))
    outgoing = _BLOB()
    try:
        if encrypt:
            protect.argtypes = [ctypes.POINTER(_BLOB), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_BLOB)]
            ok = protect(ctypes.byref(incoming), 'NOMIKO local vault', None, None, None, 0x1, ctypes.byref(outgoing))
        else:
            description = wintypes.LPWSTR()
            protect.argtypes = [ctypes.POINTER(_BLOB), ctypes.POINTER(wintypes.LPWSTR), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_BLOB)]
            ok = protect(ctypes.byref(incoming), ctypes.byref(description), None, None, None, 0x1, ctypes.byref(outgoing))
            if description:
                kernel.LocalFree(ctypes.cast(description, ctypes.c_void_p))
        if not ok:
            raise OSError(ctypes.get_last_error(), 'Windows could not unlock the local vault')
        return ctypes.string_at(outgoing.pbData, outgoing.cbData)
    finally:
        if outgoing.pbData:
            kernel.LocalFree(ctypes.cast(outgoing.pbData, ctypes.c_void_p))


class PasswordVault:
    def __init__(self, path: Path):
        self.path = path

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        plain = _crypt(self.path.read_bytes(), False)
        payload = json.loads(plain.decode('utf-8'))
        return payload if isinstance(payload, list) else []

    def write(self, items: list[dict]):
        encrypted = _crypt(json.dumps(items, ensure_ascii=False).encode('utf-8'), True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix('.tmp')
        tmp.write_bytes(encrypted)
        os.replace(tmp, self.path)
