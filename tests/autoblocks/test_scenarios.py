from datetime import timedelta

import pytest

from autoblocks.api.app_client import AutoblocksAppClient
from autoblocks.scenarios.models import GenerateMessageResponse
from autoblocks.scenarios.models import Message
from autoblocks.scenarios.models import MessageRole
from autoblocks.scenarios.models import ScenarioItem

API_KEY = "test-api-key"
APP_SLUG = "test-app"


@pytest.fixture
def client():
    return AutoblocksAppClient(APP_SLUG, API_KEY, timeout=timedelta(seconds=5))


def test_list_scenarios(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/scenarios",
        method="GET",
        status_code=200,
        json={
            "scenarios": [
                {"id": "scenario-1"},
                {"id": "scenario-2"},
            ]
        },
    )
    scenarios = client.scenarios.list_scenarios()
    assert len(scenarios) == 2
    assert isinstance(scenarios[0], ScenarioItem)
    assert scenarios[0].id == "scenario-1"
    assert scenarios[1].id == "scenario-2"


def test_generate_message(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/scenarios/scenario-1/generate-message",
        method="POST",
        status_code=200,
        json={
            "message": "Hello, how are you doing today?",
            "isFinalMessage": False,
        },
    )

    messages = [
        Message(role=MessageRole.USER, content="Hello"),
        Message(role=MessageRole.ASSISTANT, content="Hi there!"),
    ]

    response = client.scenarios.generate_message(scenario_id="scenario-1", messages=messages)
    assert isinstance(response, GenerateMessageResponse)
    assert response.message == "Hello, how are you doing today?"
    assert response.is_final_message is False


def test_generate_message_final(httpx_mock, client):
    httpx_mock.add_response(
        url=f"https://api-v2.autoblocks.ai/apps/{APP_SLUG}/scenarios/scenario-2/generate-message",
        method="POST",
        status_code=200,
        json={
            "message": "Goodbye, have a great day!",
            "isFinalMessage": True,
        },
    )

    messages = [
        Message(role=MessageRole.USER, content="I need to go now"),
        Message(role=MessageRole.ASSISTANT, content="Okay, see you later!"),
        Message(role=MessageRole.USER, content="Bye!"),
    ]

    response = client.scenarios.generate_message(scenario_id="scenario-2", messages=messages)
    assert isinstance(response, GenerateMessageResponse)
    assert response.message == "Goodbye, have a great day!"
    assert response.is_final_message is True
