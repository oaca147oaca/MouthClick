"""One MouthClick process per Windows session, released by Windows on exit."""
import atexit
import ctypes
from ctypes import wintypes

_handle = None


def acquire():
    global _handle
    if _handle is not None:
        return True
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.CreateMutexW(None, False, "Local\\MouthClick.SingleInstance")
    error = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error)
    if error == 183:
        kernel.CloseHandle(handle)
        return False
    _handle = handle
    atexit.register(kernel.CloseHandle, handle)
    return True
