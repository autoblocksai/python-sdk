import asyncio
import functools
from typing import Any
from typing import Callable

from opentelemetry import trace
from opentelemetry.baggage import set_baggage
from opentelemetry.context import attach
from opentelemetry.context import detach
from opentelemetry.context import get_current

from autoblocks._impl.context_vars import test_case_run_context_var
from autoblocks._impl.tracer.util import SpanAttribute
from autoblocks._impl.util import cuid_generator
from autoblocks._impl.util import serialize


def trace_app(app_slug: str, environment: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that wraps a function call in a new span with baggage attributes.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:

        # Support for async functions
        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # In a test case context, the span attributes are handled separately
                test_case_run_context = test_case_run_context_var.get()
                if test_case_run_context is not None:
                    return await fn(*args, **kwargs)
                execution_id = cuid_generator()
                # Get current context and set baggage
                ctx = get_current()
                ctx = set_baggage(SpanAttribute.EXECUTION_ID, execution_id, context=ctx)
                ctx = set_baggage(SpanAttribute.ENVIRONMENT, environment, context=ctx)
                ctx = set_baggage(SpanAttribute.APP_SLUG, app_slug, context=ctx)

                tracer = trace.get_tracer("AUTOBLOCKS_TRACER")
                token = attach(ctx)
                with tracer.start_as_current_span(app_slug, context=ctx) as span:
                    try:
                        # Set span attributes before function execution
                        span.set_attribute(SpanAttribute.IS_ROOT, True)
                        span.set_attribute(SpanAttribute.EXECUTION_ID, execution_id)
                        span.set_attribute(SpanAttribute.ENVIRONMENT, environment)
                        span.set_attribute(SpanAttribute.APP_SLUG, app_slug)
                        span.set_attribute(SpanAttribute.INPUT, serialize({"args": args, "kwargs": kwargs}))

                        result = await fn(*args, **kwargs)

                        # Set span attributes after function execution
                        span.set_attribute(SpanAttribute.OUTPUT, serialize(result))
                        return result
                    finally:
                        detach(token)

            return async_wrapper
        else:
            # Synchronous function support
            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                # In a test case context, the span attributes are handled separately
                test_case_run_context = test_case_run_context_var.get()
                if test_case_run_context is not None:
                    return fn(*args, **kwargs)
                execution_id = cuid_generator()
                # Get current context and set baggage
                ctx = get_current()
                ctx = set_baggage(SpanAttribute.EXECUTION_ID, execution_id, context=ctx)
                ctx = set_baggage(SpanAttribute.ENVIRONMENT, environment, context=ctx)
                ctx = set_baggage(SpanAttribute.APP_SLUG, app_slug, context=ctx)

                tracer = trace.get_tracer("AUTOBLOCKS_TRACER")
                token = attach(ctx)
                with tracer.start_as_current_span(app_slug, context=ctx) as span:
                    try:
                        span.set_attribute(SpanAttribute.IS_ROOT, True)
                        span.set_attribute(SpanAttribute.EXECUTION_ID, execution_id)
                        span.set_attribute(SpanAttribute.ENVIRONMENT, environment)
                        span.set_attribute(SpanAttribute.APP_SLUG, app_slug)
                        span.set_attribute(SpanAttribute.INPUT, serialize({"args": args, "kwargs": kwargs}))

                        result = fn(*args, **kwargs)

                        span.set_attribute(SpanAttribute.OUTPUT, serialize(result))
                        return result
                    finally:
                        detach(token)

            return sync_wrapper

    return decorator
