"""Local-user-only, memory-only EA key handoff; no DLL permission or secret file."""

import ctypes
import os
import threading
from ctypes import wintypes as w


def start_key_pipe(account: str, symbol: str, magic: int, key: bytes) -> None:
    if os.name != "nt" or len(key) != 32:
        raise ValueError("Windows and a 32-byte bridge key required")
    win_dll = getattr(ctypes, "WinDLL", None)
    win_error = getattr(ctypes, "WinError", None)
    last_error = getattr(ctypes, "get_last_error", None)
    if win_dll is None or win_error is None or last_error is None:
        raise RuntimeError("Windows native APIs unavailable")
    kernel = win_dll("kernel32", use_last_error=True)
    advapi = win_dll("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.LocalFree.argtypes = [w.HLOCAL]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    kernel.CreateNamedPipeW.argtypes = [
        w.LPCWSTR,
        w.DWORD,
        w.DWORD,
        w.DWORD,
        w.DWORD,
        w.DWORD,
        w.DWORD,
        ctypes.c_void_p,
    ]
    kernel.CreateNamedPipeW.restype = w.HANDLE
    kernel.ConnectNamedPipe.argtypes = [w.HANDLE, ctypes.c_void_p]
    kernel.WriteFile.argtypes = [
        w.HANDLE,
        ctypes.c_void_p,
        w.DWORD,
        ctypes.POINTER(w.DWORD),
        ctypes.c_void_p,
    ]
    kernel.DisconnectNamedPipe.argtypes = [w.HANDLE]
    advapi.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
    advapi.GetTokenInformation.argtypes = [
        w.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        w.DWORD,
        ctypes.POINTER(w.DWORD),
    ]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(w.LPWSTR)]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        w.LPCWSTR,
        w.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    ]

    token = w.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise win_error(last_error())
    try:
        size = w.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise win_error(last_error())
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        sid_text = w.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(sid_text)):
            raise win_error(last_error())
        try:
            acl = f"D:P(A;;GA;;;SY)(A;;GA;;;{sid_text.value})"
        finally:
            kernel.LocalFree(sid_text)
    finally:
        kernel.CloseHandle(token)
    descriptor = ctypes.c_void_p()
    if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        acl, 1, ctypes.byref(descriptor), None
    ):
        raise win_error(last_error())

    class SecurityAttributes(ctypes.Structure):
        _fields_ = [("length", w.DWORD), ("descriptor", ctypes.c_void_p), ("inherit", w.BOOL)]

    security = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
    name = rf"\\.\pipe\AurumControl-{account}-{symbol}-{magic}"
    # FIRST_PIPE_INSTANCE: refuse an existing impersonating server. Reject remote clients.
    handle = kernel.CreateNamedPipeW(
        name, 2 | 0x00080000, 8, 1, 256, 256, 1000, ctypes.byref(security)
    )
    kernel.LocalFree(descriptor)
    if handle == w.HANDLE(-1).value:
        raise win_error(last_error())

    def serve() -> None:
        try:
            while True:
                connected = kernel.ConnectNamedPipe(handle, None)
                if not connected and last_error() != 535:
                    return
                raw = key.hex().encode("ascii")
                written = w.DWORD()
                kernel.WriteFile(handle, raw, len(raw), ctypes.byref(written), None)
                # Keep data alive until the client has consumed it, then permit restart.
                kernel.FlushFileBuffers.argtypes = [w.HANDLE]
                kernel.FlushFileBuffers(handle)
                kernel.DisconnectNamedPipe(handle)
        finally:
            kernel.CloseHandle(handle)

    threading.Thread(target=serve, name="aurum-native-key", daemon=True).start()


if __name__ == "__main__":
    import argparse

    from aurum_backend.security.secrets import bridge_key

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True)
    args = parser.parse_args()
    os.environ["AURUM_KEYRING_ACCOUNT"] = f"bridge/{args.account}-XAUUSD-260110"
    value = bridge_key()
    if not value:
        raise SystemExit("Bridge key unavailable")
    start_key_pipe(args.account, "XAUUSD", 260110, value)
    print("Local-user-only native key handoff ready; no secret file or DLL required")
    threading.Event().wait()
