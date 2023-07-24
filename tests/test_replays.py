import json
import os

import requests_mock

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.config.env import env
from autoblocks.api.models import Event
from autoblocks.replays import replay_events_from_view
from autoblocks.replays import start_replay


def test_replay_events_from_view(tmp_path):
    env.AUTOBLOCKS_REPLAYS_ENABLED = True
    env.AUTOBLOCKS_REPLAYS_DIRECTORY = os.path.join(tmp_path, "autoblocks-replays")

    replay_id = start_replay()

    with requests_mock.mock() as m:
        m.get(
            f"{API_ENDPOINT}/views/123/traces",
            json={
                "nextCursor": "abc",
                "traces": [
                    {
                        "id": "trace-1",
                        "events": [
                            {
                                "id": "event-1",
                                "traceId": "trace-1",
                                "message": "message-1",
                                "timestamp": "2021-01-01T00:00:00.000Z",
                                "properties": {"x": "1"},
                            },
                        ],
                    },
                    {
                        "id": "trace-2",
                        "events": [
                            {
                                "id": "event-2",
                                "traceId": "trace-2",
                                "message": "message-2",
                                "timestamp": "2021-01-01T00:00:00.000Z",
                                "properties": {"x": "2"},
                            }
                        ],
                    },
                ],
            },
        )

        events = replay_events_from_view("mock-api-key", view_id="123", num_traces=10)

        # Nothing should be written until we iterate through the events
        assert os.listdir(os.path.join(env.AUTOBLOCKS_REPLAYS_DIRECTORY, replay_id)) == []

        # Now iterate through the events
        for event in events:
            assert isinstance(event, Event)

    with open(
        os.path.join(env.AUTOBLOCKS_REPLAYS_DIRECTORY, replay_id, "trace-1", "original", "1-message-1.json")
    ) as f:
        assert json.loads(f.read()) == {
            "message": "message-1",
            "properties": {
                "x": "1",
            },
        }
    with open(
        os.path.join(env.AUTOBLOCKS_REPLAYS_DIRECTORY, replay_id, "trace-2", "original", "1-message-2.json")
    ) as f:
        assert json.loads(f.read()) == {
            "message": "message-2",
            "properties": {
                "x": "2",
            },
        }
