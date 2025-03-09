from typing import Optional

from opentelemetry.baggage import get_baggage
from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace import Span
from opentelemetry.sdk.trace import SpanProcessor

from autoblocks._impl.context_vars import test_case_run_context_var
from autoblocks._impl.context_vars import test_run_context_var


# Custom span processor that attaches baggage values to the span on start
class ExecutionIdSpanProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        # Retrieve baggage values from the parent context
        execution_id = get_baggage("autoblocksExecutionId", context=parent_context)
        environment = get_baggage("autoblocksEnvironment", context=parent_context)
        app_id = get_baggage("autoblocksAppId", context=parent_context)
        test_case_run_context = test_case_run_context_var.get()
        test_run_context = test_run_context_var.get()

        if execution_id:
            span.set_attribute("autoblocksExecutionId", str(execution_id))
        if environment:
            span.set_attribute("autoblocksEnvironment", str(environment))
        if app_id:
            span.set_attribute("autoblocksAppId", str(app_id))

        if test_run_context:
            span.set_attribute("autoblocksRunId", str(test_run_context.run_id))
            if test_run_context.run_message:
                span.set_attribute("autoblocksRunMessage", str(test_run_context.run_message))
        elif test_case_run_context:
            span.set_attribute("autoblocksTestCaseRunId", str(test_case_run_context.run_id))

    def on_end(self, span: ReadableSpan) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
