from typing import Optional

from opentelemetry.baggage import get_baggage
from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace import SpanProcessor

from autoblocks._impl.context_vars import test_case_run_context_var
from autoblocks._impl.context_vars import test_run_context_var
from autoblocks._impl.tracer.util import SpanAttribute


# Custom span processor that attaches baggage values to the span on start
class ExecutionIdSpanProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        # Retrieve baggage values from the parent context
        execution_id = get_baggage(SpanAttribute.EXECUTION_ID, context=parent_context)
        environment = get_baggage(SpanAttribute.ENVIRONMENT, context=parent_context)
        app_slug = get_baggage(SpanAttribute.APP_SLUG, context=parent_context)
        test_case_run_context = test_case_run_context_var.get()
        test_run_context = test_run_context_var.get()

        if execution_id:
            span.set_attribute(SpanAttribute.EXECUTION_ID, str(execution_id))
        if environment:
            span.set_attribute(SpanAttribute.ENVIRONMENT, str(environment))
        if app_slug:
            span.set_attribute(SpanAttribute.APP_SLUG, str(app_slug))

        if test_run_context:
            span.set_attribute(SpanAttribute.RUN_ID, str(test_run_context.run_id))
            if test_run_context.run_message:
                span.set_attribute(SpanAttribute.RUN_MESSAGE, str(test_run_context.run_message))
        elif test_case_run_context:
            span.set_attribute(SpanAttribute.RUN_ID, str(test_case_run_context.run_id))

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
