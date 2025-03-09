from typing import Optional

from autoblocks._impl.context_vars import TestRunContext
from autoblocks._impl.context_vars import test_run_context_var
from autoblocks._impl.util import cuid_generator


def start_run(message: Optional[str] = None) -> None:
    test_run_context_var.set(TestRunContext(run_id=cuid_generator(), run_message=message))


def end_run() -> None:
    test_run_context_var.set(None)
