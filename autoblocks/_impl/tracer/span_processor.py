from typing import Optional

from opentelemetry.baggage import get_baggage
from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace import SpanProcessor

from autoblocks._impl.context_vars import get_revision_usage
from autoblocks._impl.context_vars import test_run_context_var
from autoblocks._impl.tracer.util import SpanAttribute
from autoblocks._impl.util import AutoblocksEnvVar


# Custom span processor that attaches baggage values to the span on start
class ExecutionIdSpanProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        # Retrieve baggage values from the parent context
        execution_id = get_baggage(SpanAttribute.EXECUTION_ID, context=parent_context)
        environment = get_baggage(SpanAttribute.ENVIRONMENT, context=parent_context)
        app_slug = get_baggage(SpanAttribute.APP_SLUG, context=parent_context)
        test_run_context = test_run_context_var.get()

        if execution_id:
            span.set_attribute(SpanAttribute.EXECUTION_ID, str(execution_id))
        if environment:
            span.set_attribute(SpanAttribute.ENVIRONMENT, str(environment))
        if app_slug:
            span.set_attribute(SpanAttribute.APP_SLUG, str(app_slug))

        if test_run_context:
            build_id = AutoblocksEnvVar.V2_CI_TEST_RUN_BUILD_ID.get()
            if build_id:
                span.set_attribute(SpanAttribute.BUILD_ID, str(build_id))
            span.set_attribute(SpanAttribute.RUN_ID, str(test_run_context.run_id))
            span.set_attribute(SpanAttribute.TEST_ID, str(test_run_context.test_id))
            if test_run_context.run_message:
                span.set_attribute(SpanAttribute.RUN_MESSAGE, str(test_run_context.run_message))

            revision_usage = get_revision_usage()
            if revision_usage is not None:
                revision_ids = [usage.revision_id for usage in revision_usage]
                span.set_attribute(SpanAttribute.REVISION_ID, ",".join(revision_ids))

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
