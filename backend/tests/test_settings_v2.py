import json

import pytest
from pydantic import ValidationError

from aurum_backend.models.generated_settings_v2 import EASettings
from aurum_backend.services.profiles import defaults, export_profile, export_set, import_profile
from tools.shared_settings import outputs


def test_generated_native_and_typescript_input_sources_match() -> None:
    for path, content in outputs().items():
        assert path.read_text(encoding="utf-8") == content
    model = EASettings.model_validate(defaults())
    assert len(model.model_dump()) >= 80


def test_live_and_permissions_are_disabled_by_default() -> None:
    value = defaults()
    assert value["InpExecutionMode"] == "SIGNAL_ONLY"
    for key in [
        "InpConfirmLive",
        "InpAllowRealAccount",
        "InpAllowRemoteConfig",
        "InpAllowLiveFromConfig",
    ]:
        assert value[key] is False
    assert value["InpMinNetRR"] >= 2
    for key in ["InpMlEnabled", "InpPartialCloseEnabled", "InpTrailingEnabled"]:
        assert value[key] is False


def test_profile_cannot_carry_permissions_or_unknown_fields() -> None:
    current = defaults()
    proposed = {**current, "InpRiskPerTrade": 0.4, "InpConfirmLive": True}
    raw = export_profile(proposed)
    assert "InpConfirmLive" not in raw
    assert import_profile(raw, current)["InpRiskPerTrade"] == 0.4
    bad = json.loads(raw)
    bad["values"]["InpConfirmLive"] = True
    with pytest.raises(ValueError, match="permission"):
        import_profile(json.dumps(bad), current)
    with pytest.raises(ValidationError):
        EASettings.model_validate({**current, "InpMinNetRR": 1.9})


def test_native_export_is_safe_and_uses_enum_ordinals() -> None:
    raw = export_set({**defaults(), "InpExecutionMode": "LIVE", "InpConfirmLive": True})
    assert "InpExecutionMode=0\r\n" in raw
    assert "InpConfirmLive=false\r\n" in raw
    assert "InpBrokerOffsetMode=1\r\n" in raw
    assert "HMAC" not in raw and "TOKEN" not in raw
