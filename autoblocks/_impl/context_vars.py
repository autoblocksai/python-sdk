import dataclasses
from contextvars import ContextVar
from typing import Optional


@dataclasses.dataclass
class TestCaseRunContext:
    test_id: str
    test_case_hash: str


test_case_run_context_var: ContextVar[Optional[TestCaseRunContext]] = ContextVar(
    "autoblocks_sdk_test_case_run_context_var", default=None
)
