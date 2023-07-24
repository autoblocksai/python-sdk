import json
import os

import requests_mock

from autoblocks._impl.config.constants import INGESTION_ENDPOINT
from autoblocks._impl.config.env import env
from autoblocks._impl.util import EventType
from autoblocks._impl.util import write_event_to_file_local
from autoblocks.replays import start_replay
from autoblocks.tracer import AutoblocksTracer


def test_logger_replays_local(tmp_path):
    env.AUTOBLOCKS_REPLAYS_ENABLED = True
    env.AUTOBLOCKS_REPLAYS_DIRECTORY = tmp_path

    replay_id = start_replay()
    write_event_to_file_local(
        event_type=EventType.ORIGINAL,
        trace_id="my-trace-id",
        message="my-message",
        properties=dict(x=1),
    )

    ab = AutoblocksTracer("mock-ingestion-key")

    ab.send_event(
        "my-message",
        trace_id="my-trace-id",
        properties=dict(x=1),
    )

    with open(os.path.join(tmp_path, replay_id, "my-trace-id", "replayed", "1-my-message.json")) as f:
        assert json.loads(f.read()) == {
            "message": "my-message",
            "properties": {
                "x": "1",
            },
        }


def test_logger_replays_local_with_trace_id_in_init(tmp_path):
    env.AUTOBLOCKS_REPLAYS_ENABLED = True
    env.AUTOBLOCKS_REPLAYS_DIRECTORY = tmp_path

    replay_id = start_replay()
    write_event_to_file_local(
        event_type=EventType.ORIGINAL,
        trace_id="my-trace-id",
        message="my-message",
        properties=dict(x=1),
    )

    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")

    ab.send_event(
        "my-message",
        properties=dict(x=1),
    )

    with open(os.path.join(tmp_path, replay_id, "my-trace-id", "replayed", "1-my-message.json")) as f:
        assert json.loads(f.read()) == {
            "message": "my-message",
            "properties": {
                "x": "1",
            },
        }


def test_logger_replays_ci(tmp_path):
    env.AUTOBLOCKS_REPLAYS_ENABLED = True
    env.AUTOBLOCKS_REPLAYS_FILEPATH = os.path.join(tmp_path, "replays.json")
    env.CI = True

    ab = AutoblocksTracer("mock-ingestion-key")

    ab.send_event(
        "my-message",
        trace_id="my-trace-id",
        properties=dict(x=1),
    )

    with open(env.AUTOBLOCKS_REPLAYS_FILEPATH) as f:
        assert json.loads(f.read()) == [
            {
                "traceId": "my-trace-id",
                "message": "my-message",
                "properties": {
                    "x": "1",
                },
            }
        ]


def test_logger_prod():
    ab = AutoblocksTracer("mock-ingestion-key")

    with requests_mock.mock() as m:
        m.post(
            INGESTION_ENDPOINT,
            json={"traceId": "my-trace-id"},
        )

        trace_id = ab.send_event("my-message")

    assert trace_id == "my-trace-id"
    assert m.call_count == 1

    call = m.request_history[0]
    assert call.method == "POST"
    assert call.url == INGESTION_ENDPOINT + "/"
    assert call.headers["Authorization"] == "Bearer mock-ingestion-key"
    assert call.json() == {
        "message": "my-message",
        "traceId": None,
        "timestamp": None,
        "properties": {},
    }


def test_logger_prod_with_trace_id_in_send_event():
    ab = AutoblocksTracer("mock-ingestion-key")

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message", trace_id="my-trace-id")

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": "my-trace-id",
        "timestamp": None,
        "properties": {},
    }


def test_logger_prod_with_trace_id_in_init():
    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message")

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": "my-trace-id",
        "timestamp": None,
        "properties": {},
    }


def test_logger_prod_with_trace_id_override():
    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message", trace_id="override-trace-id")

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": "override-trace-id",
        "timestamp": None,
        "properties": {},
    }


def test_logger_prod_with_set_trace_id():
    ab = AutoblocksTracer("mock-ingestion-key", trace_id="my-trace-id")
    ab.set_trace_id("override-trace-id")

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message")

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": "override-trace-id",
        "timestamp": None,
        "properties": {},
    }


def test_logger_prod_with_properties():
    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message")

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": None,
        "timestamp": None,
        "properties": dict(x=1),
    }


def test_logger_prod_with_set_properties():
    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.set_properties(dict(y=2))

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message")

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": None,
        "timestamp": None,
        "properties": dict(y=2),
    }


def test_logger_prod_with_update_properties():
    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.update_properties(dict(y=2))

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message")

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": None,
        "timestamp": None,
        "properties": dict(x=1, y=2),
    }


def test_logger_prod_with_update_properties_and_send_event_properties():
    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.update_properties(dict(y=2))

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message", properties=dict(z=3))

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": None,
        "timestamp": None,
        "properties": dict(x=1, y=2, z=3),
    }


def test_logger_prod_with_properties_with_conflicting_keys():
    ab = AutoblocksTracer("mock-ingestion-key", properties=dict(x=1))
    ab.update_properties(dict(y=2))

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message", properties=dict(x=3, z=3))

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": None,
        "timestamp": None,
        "properties": dict(x=3, y=2, z=3),
    }


def test_logger_prod_with_timestamp():
    ab = AutoblocksTracer("mock-ingestion-key")

    with requests_mock.mock() as m:
        m.post(INGESTION_ENDPOINT, json={})
        ab.send_event("my-message", timestamp="2023-07-24T21:52:52.742Z")

    assert m.request_history[0].json() == {
        "message": "my-message",
        "traceId": None,
        "timestamp": "2023-07-24T21:52:52.742Z",
        "properties": {},
    }


def test_logger_prod_catches_errors():
    ab = AutoblocksTracer("mock-ingestion-key")

    with requests_mock.mock() as m:
        m.post(
            INGESTION_ENDPOINT,
            exc=Exception("mock error"),
        )

        # This will log the error but not throw
        trace_id = ab.send_event("my-message")

    assert trace_id is None
