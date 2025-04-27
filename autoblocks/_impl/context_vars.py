import dataclasses
from contextvars import ContextVar
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from autoblocks._impl.util import StrEnum
from autoblocks._impl.util import now_iso_8601


class RevisionType(StrEnum):
    PROMPT = "prompt"
    CONFIG = "config"


@dataclasses.dataclass
class RevisionUsage:
    entity_id: str
    entity_type: RevisionType
    revision_id: str
    used_at: str

    def serialize(self) -> Dict[str, str]:
        return dict(
            entityExternalId=self.entity_id,
            entityType=self.entity_type.value,
            revisionId=self.revision_id,
            usedAt=self.used_at,
        )


@dataclasses.dataclass
class TestCaseRunContext:
    run_id: str
    test_id: str
    test_case_hash: str
    revision_usage: List[RevisionUsage] = dataclasses.field(default_factory=list)


test_case_run_context_var: ContextVar[Optional[TestCaseRunContext]] = ContextVar(
    "autoblocks_sdk_test_case_run_context_var",
    default=None,
)


@dataclasses.dataclass
class TestRunContext:
    run_id: str
    run_message: Optional[str]
    test_id: str


test_run_context_var: ContextVar[Optional[TestRunContext]] = ContextVar(
    "autoblocks_sdk_test_run_context_var",
    default=None,
)


@dataclasses.dataclass
class EvaluatorRunContext:
    revision_usage: List[RevisionUsage] = dataclasses.field(default_factory=list)


evaluator_run_context_var: ContextVar[Optional[EvaluatorRunContext]] = ContextVar(
    "autoblocks_sdk_evaluator_run_context_var",
    default=None,
)


def get_current_run_context() -> Optional[Union[EvaluatorRunContext, TestCaseRunContext]]:
    # Check the narrower evaluator_run_context first so that we can detect if a prompt
    # is being used in the context of an evaluator. Otherwise, fall back to the wider
    # test_case_run_context.
    return evaluator_run_context_var.get() or test_case_run_context_var.get()


def register_revision_usage(
    entity_id: str,
    entity_type: RevisionType,
    revision_id: str,
) -> None:
    ctx = get_current_run_context()
    if ctx is None:
        return

    ctx.revision_usage.append(
        RevisionUsage(
            entity_id=entity_id,
            entity_type=entity_type,
            revision_id=revision_id,
            used_at=now_iso_8601(),
        ),
    )


def get_revision_usage() -> Optional[List[RevisionUsage]]:
    ctx = get_current_run_context()
    return ctx.revision_usage if ctx else None


grid_search_context_var: ContextVar[Optional[dict[str, Any]]] = ContextVar(
    "autoblocks_sdk_grid_search_context_var",
    default=None,
)


def grid_search_ctx() -> Optional[dict[str, Any]]:
    return grid_search_context_var.get()
