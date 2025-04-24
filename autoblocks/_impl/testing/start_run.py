from typing import Optional
from typing import Sequence

from autoblocks._impl.context_vars import TestRunContext
from autoblocks._impl.context_vars import test_run_context_var
from autoblocks._impl.testing.models import BaseAutoTracerEvaluator
from autoblocks._impl.util import cuid_generator


def start_run(
    message: Optional[str] = None,
    evaluators: Optional[Sequence[BaseAutoTracerEvaluator]] = None,
) -> None:
    """
    Can be used to start a test run when using the auto tracer.
    """
    if test_run_context_var.get() is not None:
        raise RuntimeError("Cannot start a new run while another run is active. Did you forget to call end_run()?")
    test_run_context_var.set(TestRunContext(run_id=cuid_generator(), run_message=message, evaluators=evaluators))


def end_run() -> None:
    """
    Used in conjunction with `start_run` to end a test run when using the auto tracer.
    """
    test_run_context_var.set(None)
