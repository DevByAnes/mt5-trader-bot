import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from jsonschema import ValidationError as SchemaError
from pydantic import ValidationError

from aurum_backend.core.resources import FIXTURES, OPENAPI, SETTINGS
from aurum_backend.models import generated
from aurum_backend.models.base import validate_schema
from aurum_backend.models.generated import CommandRequest, SettingsDraft
from aurum_backend.models.generated_settings import SettingsMetadataValues
from tools.gen_models import TARGET, outputs


def test_regeneration_is_byte_identical() -> None:
    for filename, content in outputs().items():
        assert (TARGET / filename).read_text(encoding="utf-8") == content, filename


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda p: p.stem)
def test_all_fixture_envelopes_validate_in_generated_models(path: Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    model = getattr(generated, path.stem + "Envelope")
    parsed = model.model_validate(value)
    validate_schema(path.stem + "Envelope", parsed.model_dump(mode="json", exclude_unset=True))


def test_optional_does_not_mean_nullable() -> None:
    assert CommandRequest.model_validate({}).position_id is None
    with pytest.raises(ValidationError):
        CommandRequest.model_validate({"position_id": None})


@given(st.one_of(st.floats(allow_infinity=True, allow_nan=True), st.booleans(), st.text()))
@settings(max_examples=100, deadline=None)
def test_settings_models_do_not_relax_schema(value: Any) -> None:
    fixture = json.loads((FIXTURES / "SettingsData.json").read_text(encoding="utf-8"))["data"][
        "values"
    ]
    fixture["riskPerTrade"] = value
    expected = True
    try:
        validate_schema("SettingsMetadataValues", fixture)
    except (SchemaError, ValueError):
        expected = False
    for model in [SettingsMetadataValues, SettingsDraft]:
        accepted = True
        try:
            model.model_validate(fixture)
        except ValidationError:
            accepted = False
        assert accepted == expected


def test_all_settings_enum_values_and_constraints_agree() -> None:
    properties: Any = SETTINGS["properties"]
    components: Any = OPENAPI["components"]
    source = components["schemas"]["SettingsDraft"]["properties"]
    base = json.loads((FIXTURES / "SettingsData.json").read_text(encoding="utf-8"))["data"][
        "values"
    ]
    for key, metadata in properties.items():
        for constraint in ["type", "minimum", "maximum", "multipleOf"]:
            assert metadata.get(constraint) == source[key].get(constraint)
        for choice in metadata["enum"]:
            candidate = {**base, key: choice}
            SettingsDraft.model_validate(candidate)
            SettingsMetadataValues.model_validate(candidate)
