from typing import cast

from starlette.requests import Request

from aurum_backend.fixtures.state import FixtureState


def fixture_state(request: Request) -> FixtureState:
    return cast(FixtureState, request.app.state.fixture_state)
