import logging
import os
from datetime import datetime
from typing import List

import pytest

from autoblocks._impl.config.constants import AUTOBLOCKS_REPLAY_ID
from autoblocks._impl.util import make_replay_run
from autoblocks._impl.vendor.openai.patch import trace_openai
from autoblocks._impl.vendor.openai.patch import tracer

log = logging.getLogger(__name__)
autoblocks_enabled = "--autoblocks"
openai_tracing_enabled = "--trace-openai"


def pytest_addoption(parser: pytest.Parser):
    parser.addoption(autoblocks_enabled, action="store_true", help="Enable Autoblocks replays.")
    parser.addoption(openai_tracing_enabled, action="store_true", help="Enable OpenAI automated tracing.")


def pytest_sessionstart(session: pytest.Session):
    if not session.config.getoption(autoblocks_enabled):
        return

    if session.config.getoption(openai_tracing_enabled):
        try:
            trace_openai()
        except Exception as err:
            log.error(f"trace_openai() failed: {err}", exc_info=True)

    home = os.path.basename(os.path.expanduser("~"))
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    os.environ[AUTOBLOCKS_REPLAY_ID] = f"{home}-pytest-{now}"


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: List[pytest.Item]):
    if not config.getoption(autoblocks_enabled):
        return

    if not config.getoption(openai_tracing_enabled):
        return

    try:
        import wrapt
    except ImportError:
        raise ImportError(
            "You must have wrapt installed in order to use the pytest plugin. Install it with `pip install wrapt`."
        )

    @wrapt.function_wrapper
    def set_trace_id_wrapper(wrapped, instance, args, kwargs):
        tracer.set_trace_id(wrapped.__name__)
        return wrapped(*args, **kwargs)

    for item in items:
        item.obj = set_trace_id_wrapper(item.obj)


def pytest_terminal_summary(terminalreporter, exitstatus, config: pytest.Config):
    if not config.getoption(autoblocks_enabled):
        return

    run = make_replay_run()
    run_html_url = run.html_url if run else None
    if run_html_url:
        terminalreporter.write_sep("=", "Autoblocks Replay Results", blue=True, bold=True)
        terminalreporter.write_line(f"View your replay: {run_html_url}")
        terminalreporter.write_sep("=", blue=True, bold=True)

    os.environ.pop(AUTOBLOCKS_REPLAY_ID, None)
