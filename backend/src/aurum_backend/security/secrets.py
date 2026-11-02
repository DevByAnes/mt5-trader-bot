"""Explicit environment or OS keyring lookup; no file fallback or automatic provisioning."""

import os

import keyring


def bridge_key() -> bytes | None:
    raw = os.environ.get("AURUM_BRIDGE_KEY_HEX")
    account = os.environ.get("AURUM_KEYRING_ACCOUNT")
    if raw is None and account:
        if not account.startswith("bridge/"):
            raise ValueError("Keyring account must be scoped to bridge/")
        backend = keyring.get_keyring()
        if not type(backend).__module__.startswith(
            ("keyring.backends.Windows", "keyring.backends.macOS", "keyring.backends.SecretService")
        ):
            raise ValueError("Only an explicit OS credential backend is permitted")
        try:
            raw = keyring.get_password("AurumControl", account)
        except keyring.errors.KeyringError:
            raise ValueError("OS keyring unavailable") from None
    if not raw:
        return None
    try:
        value = bytes.fromhex(raw)
    except ValueError:
        raise ValueError("Invalid bridge key encoding") from None
    if len(value) < 32:
        raise ValueError("Bridge key too short")
    return value
