import logging
import os
from datetime import datetime
from typing import Generator
from typing import Optional

from autoblocks._impl.api.client import AutoblocksAPIClient
from autoblocks._impl.api.models import Event
from autoblocks._impl.config.env import env
from autoblocks._impl.util import EventType
from autoblocks._impl.util import write_event_to_file_ci
from autoblocks._impl.util import write_event_to_file_local

log = logging.getLogger(__name__)


def start_replay() -> Optional[str]:
    """
    Generate a replay ID if we're replaying locally. This allows you to run replays
    over and over without overwriting past replays.
    """
    if env.CI:
        log.info("Skipping creating replay directory. In CI environments, all replays are written to a single file.")
        return None

    replay_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    # Create the directory for this replay
    os.makedirs(
        os.path.join(
            env.AUTOBLOCKS_REPLAYS_DIRECTORY,
            replay_id,
        ),
        exist_ok=True,
    )

    log.info(f"Your replay ID is {replay_id}")
    return replay_id


def replay_events_from_view(api_key: str, *, view_id: str, num_traces: int) -> Generator[Event, None, None]:
    """
    Replays events from a view by writing them to a local file. It is expected that these events will be replayed
    through the user's application and generate send_event calls from the Autoblocks SDK. The SDK will write the
    replayed events to a different file, which can be used to compare the original and replayed events.
    """
    resp = AutoblocksAPIClient(api_key).get_traces_from_view(view_id, page_size=num_traces)
    for trace in resp.traces:
        for event in trace.events:
            log.info(f"Replaying event {event}")

            if env.CI:
                write_event_to_file_ci(
                    trace_id=trace.id,
                    message=event.message,
                    properties=event.properties,
                )
            else:
                write_event_to_file_local(
                    event_type=EventType.ORIGINAL,
                    trace_id=trace.id,
                    message=event.message,
                    properties=event.properties,
                )
            yield event
