import json
import os

import pytest

from autoblocks._impl.config.env import env
from autoblocks._impl.error import NoReplayInProgressException
from autoblocks._impl.util import EventType
from autoblocks._impl.util import convert_values_to_strings
from autoblocks._impl.util import write_event_to_file_ci
from autoblocks._impl.util import write_event_to_file_local
from autoblocks.replays import start_replay


def test_convert_values_to_strings():
    assert convert_values_to_strings(
        {
            "none": None,
            "str": "str",
            "int": 1,
            "float": 1.0,
            "bool": True,
            "dict": {
                "str": "str",
                "int": 2,
                "float": 2.0,
                "bool": False,
                "list": ["str", 3, True, {"d": "d"}],
            },
        }
    ) == {
        "none": "null",
        "str": "str",
        "int": "1",
        "float": "1.0",
        "bool": "true",
        "dict": {
            "str": "str",
            "int": "2",
            "float": "2.0",
            "bool": "false",
            "list": ["str", "3", "true", {"d": "d"}],
        },
    }


def test_write_file_no_replay_in_progress(tmp_path):
    env.AUTOBLOCKS_REPLAYS_ENABLED = True
    env.AUTOBLOCKS_REPLAYS_DIRECTORY = tmp_path

    with pytest.raises(NoReplayInProgressException):
        write_event_to_file_local(
            event_type=EventType.ORIGINAL,
            trace_id="my-trace-id",
            message="my-message",
            properties=dict(x=1),
        )


def test_write_file_with_replay_id(tmp_path):
    env.AUTOBLOCKS_REPLAYS_ENABLED = True
    env.AUTOBLOCKS_REPLAYS_DIRECTORY = tmp_path

    replay_id = start_replay()
    write_event_to_file_local(
        event_type=EventType.ORIGINAL,
        trace_id="my-trace-id",
        message="my-message",
        properties=dict(x=1),
    )

    assert os.listdir(tmp_path) == [replay_id]
    with open(os.path.join(tmp_path, replay_id, "my-trace-id", "original", "1-my-message.json")) as f:
        assert json.loads(f.read()) == {
            "message": "my-message",
            "properties": {
                "x": "1",
            },
        }


def test_write_file_appends_to_most_recent_replay(tmp_path):
    env.AUTOBLOCKS_REPLAYS_ENABLED = True
    env.AUTOBLOCKS_REPLAYS_DIRECTORY = tmp_path

    replay_id_1 = start_replay()
    write_event_to_file_local(
        event_type=EventType.ORIGINAL,
        trace_id="trace-1",
        message="message-1",
    )
    replay_id_2 = start_replay()
    write_event_to_file_local(
        event_type=EventType.ORIGINAL,
        trace_id="trace-2",
        message="message-2",
    )

    # This should get appended to replay-2 since it's the last active replay
    write_event_to_file_local(
        event_type=EventType.ORIGINAL,
        trace_id="trace-3",
        message="message-3",
    )

    assert sorted(os.listdir(tmp_path)) == [replay_id_1, replay_id_2]
    assert sorted(os.listdir(os.path.join(tmp_path, replay_id_1))) == ["trace-1"]
    assert sorted(os.listdir(os.path.join(tmp_path, replay_id_2))) == ["trace-2", "trace-3"]


def test_write_file_adds_index_prefix(tmp_path):
    env.AUTOBLOCKS_REPLAYS_ENABLED = True
    env.AUTOBLOCKS_REPLAYS_DIRECTORY = tmp_path

    replay_id = start_replay()
    write_event_to_file_local(
        event_type=EventType.ORIGINAL,
        trace_id="my-trace-id",
        message="message",
    )
    write_event_to_file_local(
        event_type=EventType.ORIGINAL,
        trace_id="my-trace-id",
        message="message",
    )

    assert sorted(os.listdir(os.path.join(tmp_path, replay_id, "my-trace-id", "original"))) == [
        "1-message.json",
        "2-message.json",
    ]


def test_write_event_file_to_ci(tmp_path):
    env.AUTOBLOCKS_REPLAYS_ENABLED = True
    env.AUTOBLOCKS_REPLAYS_FILEPATH = os.path.join(tmp_path, "replays.json")
    env.CI = True

    write_event_to_file_ci(
        trace_id="trace-1",
        message="message-1",
        properties=dict(x=1),
    )
    write_event_to_file_ci(
        trace_id="trace-2",
        message="message-2",
        properties=dict(x=2),
    )

    with open(env.AUTOBLOCKS_REPLAYS_FILEPATH) as f:
        assert json.loads(f.read()) == [
            {
                "traceId": "trace-1",
                "message": "message-1",
                "properties": {
                    "x": "1",
                },
            },
            {
                "traceId": "trace-2",
                "message": "message-2",
                "properties": {
                    "x": "2",
                },
            },
        ]
