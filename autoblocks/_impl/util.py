import json
import os
from enum import Enum
from typing import Dict
from typing import Optional

from autoblocks._impl.config.env import env
from autoblocks._impl.error import NoReplayInProgressException


class EventType(str, Enum):
    ORIGINAL = "original"
    REPLAYED = "replayed"


def convert_values_to_strings(x) -> Dict:
    """
    Convert all values in a dictionary to strings.

    We do this because under the hood, Autoblocks stores all property values as strings.
    In order to effectively diff original vs replayed events, we need to ensure that
    the values are the same type.
    """
    if x is None:
        return "null"
    elif isinstance(x, dict):
        return {k: convert_values_to_strings(v) for k, v in x.items()}
    elif isinstance(x, list):
        return [convert_values_to_strings(item) for item in x]
    elif isinstance(x, bool):
        return str(x).lower()
    elif isinstance(x, (int, float)):
        if int(x) == x:
            return str(int(x))
        else:
            return str(x)
    else:
        return x


def write_event_to_file_local(
    event_type: EventType,
    trace_id: str,
    message: str,
    properties: Optional[Dict] = None,
) -> None:
    """
    In local environments we write the replayed events to a directory structure
    that looks like this:

    autoblocks-replays/
        <replay-id>/
            <trace-id>/
                original/
                    <event-number>-<message>.json
                replayed/
                    <event-number>-<message>.json
    """
    # Assume the last folder in the replay directory is the current replay folder
    # if not explicitly specified
    current_replays = os.listdir(env.AUTOBLOCKS_REPLAYS_DIRECTORY)
    if not current_replays:
        raise NoReplayInProgressException(
            "No replay is currently in progress. Call autoblocks.replays.start_replay to start a replay."
        )
    replay_id = sorted(current_replays)[-1]

    directory = os.path.join(
        env.AUTOBLOCKS_REPLAYS_DIRECTORY,
        replay_id,
        trace_id,
        event_type,
    )

    os.makedirs(directory, exist_ok=True)

    num_existing_replayed_events = len(os.listdir(directory))

    filename = os.path.join(
        directory,
        # Prefix with the replay number so that the replayed files are sorted
        # by replay order
        f"{num_existing_replayed_events + 1}-{message.replace(' ', '-')}.json",
    )

    with open(filename, "w") as f:
        f.write(
            json.dumps(
                {
                    "message": message,
                    "properties": convert_values_to_strings(properties),
                },
                indent=2,
                sort_keys=True,
            )
        )


def write_event_to_file_ci(
    trace_id: str,
    message: str,
    properties: Optional[Dict] = None,
) -> None:
    """
    In CI environments we just write all the traces to one file. This makes it
    a bit easier for the downstream GitHub Actions job to process the replayed traces.
    """
    # If the replays file doesn't exist, create it
    if not os.path.exists(env.AUTOBLOCKS_REPLAYS_FILEPATH):
        with open(env.AUTOBLOCKS_REPLAYS_FILEPATH, "w") as f:
            f.write(json.dumps([]))

    # Read the file and append the new event
    with open(env.AUTOBLOCKS_REPLAYS_FILEPATH, "r") as f:
        content = json.loads(f.read())

    with open(env.AUTOBLOCKS_REPLAYS_FILEPATH, "w") as f:
        content.append(
            {
                "traceId": trace_id,
                "message": message,
                "properties": convert_values_to_strings(properties),
            }
        )
        f.write(json.dumps(content, indent=2, sort_keys=True))
