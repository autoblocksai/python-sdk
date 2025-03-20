import pytest

from autoblocks._impl.config.constants import V2_API_ENDPOINT

TEST_APP_ID = "jqg74mpzzovssq38j055yien"

@pytest.fixture
def v2_api_endpoint():
    """Return the V2 API endpoint from constants."""
    return V2_API_ENDPOINT

@pytest.fixture
def test_app_id():
    """Return the test app ID used across tests."""
    return TEST_APP_ID

@pytest.fixture
def mock_v2_env_vars(monkeypatch):
    """Set up mock environment variables for V2 tests."""
    monkeypatch.setenv("AUTOBLOCKS_V2_API_KEY", "mock-v2-api-key")
    return {
        "AUTOBLOCKS_V2_API_KEY": "mock-v2-api-key",
    } 