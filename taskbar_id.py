"""Gives the Humnote window its own identity on the Windows taskbar.

The app runs in a Chrome app window, which Windows would otherwise group (and pin) as just another
Chrome window. This sets the window's AppUserModelID plus the "relaunch" properties, so the taskbar
groups it as Humnote, shows the Humnote icon, and a pinned icon starts the app through its launcher.
Plain ctypes (no extra packages).
"""
import ctypes, sys
from ctypes import wintypes

APP_ID = "Humnote.App"
TITLE = "Humnote"


class GUID(ctypes.Structure):
    _fields_ = [("d1", ctypes.c_ulong), ("d2", ctypes.c_ushort), ("d3", ctypes.c_ushort), ("d4", ctypes.c_ubyte * 8)]

    def __init__(self, s):
        import uuid
        u = uuid.UUID(s)
        super().__init__(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))


class PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", ctypes.c_ulong)]


class PROPVARIANT(ctypes.Structure):
    _fields_ = [("vt", ctypes.c_ushort), ("r1", ctypes.c_ushort), ("r2", ctypes.c_ushort), ("r3", ctypes.c_ushort),
                ("p", ctypes.c_void_p), ("p2", ctypes.c_void_p)]


FMT = "{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"
PKEY_ID, PKEY_CMD, PKEY_ICON, PKEY_NAME = (PROPERTYKEY(GUID(FMT), n) for n in (5, 2, 3, 4))
IID_IPropertyStore = GUID("{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}")
VT_LPWSTR, VT_EMPTY = 31, 0

shell32 = ctypes.windll.shell32
user32 = ctypes.windll.user32
ole32 = ctypes.windll.ole32


def _store(hwnd):
    ptr = ctypes.c_void_p()
    hr = shell32.SHGetPropertyStoreForWindow(wintypes.HWND(hwnd), ctypes.byref(IID_IPropertyStore), ctypes.byref(ptr))
    if hr != 0 or not ptr.value:
        return None
    return ptr


def _vcall(obj, index, restype, *args):
    vtbl = ctypes.cast(ctypes.cast(obj, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    fn = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *[type(a) for a in args])(vtbl[index])
    return fn(obj, *args)


def _set(store, key, text):
    pv = PROPVARIANT()
    buf = None
    if text is None:
        pv.vt = VT_EMPTY
    else:
        buf = ctypes.create_unicode_buffer(text)
        pv.vt = VT_LPWSTR
        pv.p = ctypes.cast(buf, ctypes.c_void_p).value
    # IPropertyStore: 0 QI, 1 AddRef, 2 Release, 3 GetCount, 4 GetAt, 5 GetValue, 6 SetValue, 7 Commit
    return _vcall(store, 6, ctypes.c_long, ctypes.pointer(key), ctypes.pointer(pv))


def _get_id(store):
    pv = PROPVARIANT()
    if _vcall(store, 5, ctypes.c_long, ctypes.pointer(PKEY_ID), ctypes.pointer(pv)) != 0 or pv.vt != VT_LPWSTR:
        return None
    return ctypes.wstring_at(pv.p)


def tag_window(hwnd, relaunch_cmd, icon_path):
    """Sets Humnote's taskbar identity on one window. Returns True if it is (now) tagged."""
    st = _store(hwnd)
    if not st:
        return False
    try:
        if _get_id(st) == APP_ID:
            return True
        _set(st, PKEY_CMD, relaunch_cmd)
        _set(st, PKEY_ICON, icon_path)
        _set(st, PKEY_NAME, TITLE)
        _set(st, PKEY_ID, APP_ID)
        _vcall(st, 7, ctypes.c_long)
        return True
    finally:
        _vcall(st, 2, ctypes.c_ulong)


def find_windows(title=TITLE):
    found = []
    EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(h, _):
        if user32.IsWindowVisible(h):
            n = user32.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, b, n + 1)
            if b.value == title:
                found.append(h)
        return True

    user32.EnumWindows(EnumProc(cb), 0)
    return found


def keep_tagged(relaunch_cmd, icon_path, alive, period=1.0):
    """Run in a thread: tags every Humnote window while alive() is true."""
    import time
    ole32.CoInitialize(None)
    while alive():
        for h in find_windows():
            try:
                tag_window(h, relaunch_cmd, icon_path)
            except Exception:
                pass
        time.sleep(period)


if __name__ == "__main__":  # quick check: tag any open Humnote window now
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    cmd = f'"{sys.executable.replace("python.exe", "pythonw.exe")}" "{os.path.join(here, "Hum to MIDI.pyw")}"'
    ole32.CoInitialize(None)
    for h in find_windows():
        print(h, tag_window(h, cmd, os.path.join(here, "icon.ico")))
