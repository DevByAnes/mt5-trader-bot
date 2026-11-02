import pytest

from aurum_backend.security.secrets import bridge_key


def test_secret_environment_and_scoped_keyring(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = bytes(range(32))
    monkeypatch.setenv("AURUM_BRIDGE_KEY_HEX", expected.hex())
    assert bridge_key() == expected
    monkeypatch.delenv("AURUM_BRIDGE_KEY_HEX")
    monkeypatch.setenv("AURUM_KEYRING_ACCOUNT", "bridge/demo")
    native = type("NativeKeyring", (), {"__module__": "keyring.backends.Windows"})()
    monkeypatch.setattr("aurum_backend.security.secrets.keyring.get_keyring", lambda: native)
    calls = []

    def read(service: str, account: str) -> str:
        calls.append((service, account))
        return expected.hex()

    monkeypatch.setattr("aurum_backend.security.secrets.keyring.get_password", read)
    assert bridge_key() == expected
    assert calls == [("AurumControl", "bridge/demo")]
    monkeypatch.setenv("AURUM_KEYRING_ACCOUNT", "unrelated-service")
    with pytest.raises(ValueError, match="scoped"):
        bridge_key()
