import pytest

from autoblocks._impl.config.env import env


@pytest.fixture(autouse=True)
def reset_env():
    env.CI = False
    env.AUTOBLOCKS_REPLAYS_ENABLED = False
    env.AUTOBLOCKS_REPLAYS_DIRECTORY = "autoblocks-replays"
    env.AUTOBLOCKS_REPLAYS_FILEPATH = "replays.json"
    yield
