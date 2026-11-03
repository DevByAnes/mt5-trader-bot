"""New native Demo mode stays explicit; no Python execution or fabricated telemetry."""

from pathlib import Path
from uuid import uuid4

import pytest

from aurum_backend.api.errors import ApiFault
from aurum_backend.models.generated import EaState, SettingsDraft
from aurum_backend.services.file_state import FileState

from .test_bridge_file import file_config, message


def test_auto_mode_schema_and_native_opt_in(tmp_path: Path) -> None:
    state = FileState(file_config(tmp_path))
    try:
        snapshot = message()
        resources = snapshot["body"]["resources"]
        resources["SettingsData"]["values"]["executionMode"] = "SIGNAL_ONLY"
        state.files.write("state.json", state.codec.encode(snapshot))
        state.poll()
        values = {**state.read("SettingsData")["values"], "executionMode": "AUTO_EXECUTE"}
        SettingsDraft.model_validate(values)
        with pytest.raises(ApiFault, match="explicitly in MT5") as denied:
            state.accept("/settings/apply", str(uuid4()), {"base_version": 7, "values": values})
        assert denied.value.status == 403
    finally:
        state.close()


def test_signed_native_auto_telemetry_and_safe_downgrade(tmp_path: Path) -> None:
    state = FileState(file_config(tmp_path))
    try:
        snapshot = message()
        resources = snapshot["body"]["resources"]
        resources["EaState"]["mode"] = "AUTO_EXECUTE"
        resources["EaState"]["h1_strength"] = None
        resources["EaState"]["h4_strength"] = None
        resources["SettingsData"]["values"]["executionMode"] = "AUTO_EXECUTE"
        resources["Validation"] = None
        EaState.model_validate(resources["EaState"])
        state.files.write("state.json", state.codec.encode(snapshot))
        state.poll()
        assert state.read("EaState")["mode"] == "AUTO_EXECUTE"
        assert state.read("EaState")["h1_strength"] is None
        with pytest.raises(ApiFault, match="not reported"):
            state.read("Validation")
        values = {**state.read("SettingsData")["values"], "executionMode": "SIGNAL_ONLY"}
        accepted = state.accept(
            "/settings/apply", str(uuid4()), {"base_version": 7, "values": values}
        )
        assert accepted["data"]["status"] == "PENDING"
    finally:
        state.close()
