import os
from datetime import datetime
from typing import List

import pytest
import wrapt

from autoblocks._impl.config.constants import AUTOBLOCKS_SIMULATION_ID
from autoblocks._impl.util import make_replay_run
from autoblocks._impl.vendor.openai.patch import patch_openai
from autoblocks._impl.vendor.openai.patch import patch_tracer

autoblocks_enabled = "--autoblocks"


def pytest_addoption(parser: pytest.Parser):
    parser.addoption(autoblocks_enabled, action="store_true", help="Enable Autoblocks simulations.")


def pytest_sessionstart(session: pytest.Session):
    if not session.config.getoption(autoblocks_enabled):
        return

    patch_openai()

    home = os.path.basename(os.path.expanduser("~"))
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    os.environ[AUTOBLOCKS_SIMULATION_ID] = f"{home}-pytest-{now}"


@wrapt.function_wrapper
def set_trace_id_wrapper(wrapped, instance, args, kwargs):
    patch_tracer.set_trace_id(wrapped.__name__)
    return wrapped(*args, **kwargs)


def pytest_collection_modifyitems(session: pytest.Session, config: pytest.Config, items: List[pytest.Item]):
    if not config.getoption(autoblocks_enabled):
        return

    for item in items:
        item.obj = set_trace_id_wrapper(item.obj)


def pytest_terminal_summary(terminalreporter, exitstatus, config: pytest.Config):
    if not config.getoption(autoblocks_enabled):
        return

    run = make_replay_run()
    run_html_url = run.html_url if run else None
    if run_html_url:
        terminalreporter.write_sep("=", "Autoblocks Simulation Results", blue=True, bold=True)
        terminalreporter.write_line(f"View your simulation: {run_html_url}")
        terminalreporter.write_sep("=", blue=True, bold=True)

    os.environ.pop(AUTOBLOCKS_SIMULATION_ID, None)
