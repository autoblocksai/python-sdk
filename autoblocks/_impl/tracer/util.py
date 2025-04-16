from autoblocks._impl.util import StrEnum


class SpanAttribute(StrEnum):
    IS_ROOT = "autoblocksIsRoot"
    EXECUTION_ID = "autoblocksExecutionId"
    ENVIRONMENT = "autoblocksEnvironment"
    APP_SLUG = "autoblocksAppSlug"
    INPUT = "autoblocksInput"
    OUTPUT = "autoblocksOutput"
    RUN_ID = "autoblocksRunId"
    RUN_MESSAGE = "autoblocksRunMessage"
