from contextvars import ContextVar
from typing import Optional

current_external_test_id: ContextVar[Optional[str]] = ContextVar(
    "autoblocks_sdk_current_external_test_id", default=None
)
current_test_case_hash: ContextVar[Optional[str]] = ContextVar("autoblocks_sdk_current_test_case_hash", default=None)
