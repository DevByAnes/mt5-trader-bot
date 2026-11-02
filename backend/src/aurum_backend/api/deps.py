from typing import cast

from starlette.requests import Request

from aurum_backend.fixtures.state import FixtureState
from aurum_backend.services.file_state import FileState


def fixture_state(request: Request) -> FixtureState | FileState:
    return cast(FixtureState | FileState, request.app.state.fixture_state)
