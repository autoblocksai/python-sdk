import dataclasses
from contextvars import ContextVar
from typing import Dict
from typing import List
from typing import Optional

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
    test_id: str
    test_case_hash: str
    revision_usage: List[RevisionUsage] = dataclasses.field(default_factory=list)


test_case_run_context_var: ContextVar[Optional[TestCaseRunContext]] = ContextVar(
    "autoblocks_sdk_test_case_run_context_var",
    default=None,
)


def register_test_case_revision_usage(
    entity_id: str,
    entity_type: RevisionType,
    revision_id: str,
) -> None:
    ctx = test_case_run_context_var.get()
    if ctx is None:
        # Shouldn't happen, but just return
        return

    ctx.revision_usage.append(
        RevisionUsage(
            entity_id=entity_id,
            entity_type=entity_type,
            revision_id=revision_id,
            used_at=now_iso_8601(),
        ),
    )


def get_test_case_revision_usage() -> Optional[List[RevisionUsage]]:
    ctx = test_case_run_context_var.get()
    return ctx.revision_usage if ctx else None
