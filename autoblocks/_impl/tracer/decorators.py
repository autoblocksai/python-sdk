import asyncio
import dataclasses
import functools
import uuid
from typing import Any
from typing import Callable

from opentelemetry import trace
from opentelemetry.baggage import set_baggage
from opentelemetry.context import attach
from opentelemetry.context import detach
from opentelemetry.context import get_current

from autoblocks._impl.testing.util import serialize as serialize_testing
from autoblocks._impl.tracer.util import SpanAttribute
from autoblocks._impl.util import cuid_generator


def serialize(value: Any) -> Any:
    try:
        # See https://docs.python.org/3/library/dataclasses.html#dataclasses.is_dataclass:
        # isinstance(test_case, type) checks test_case is an instance and not a type
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            serialized: dict[Any, Any] = {}
            for k, v in dataclasses.asdict(value).items():
                try:
                    serialized[k] = serialize_testing(v)
                except Exception:
                    # Skip over non-serializable test case attributes
                    pass
            return serialized

        return serialize_testing(value)
    except Exception:
        return str(value)


def trace_app(app_id: str, environment: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that wraps a function call in a new span with baggage attributes.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        # Support for async functions
        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                execution_id = cuid_generator()
                # Get current context and set baggage
                ctx = get_current()
                ctx = set_baggage(SpanAttribute.EXECUTION_ID, execution_id, context=ctx)
                ctx = set_baggage(SpanAttribute.ENVIRONMENT, environment, context=ctx)
                ctx = set_baggage(SpanAttribute.APP_ID, app_id, context=ctx)

                tracer = trace.get_tracer("AUTOBLOCKS_TRACER")
                token = attach(ctx)
                with tracer.start_as_current_span(app_id, context=ctx) as span:
                    try:
                        # Set span attributes before function execution
                        span.set_attribute(SpanAttribute.IS_ROOT, True)
                        span.set_attribute(SpanAttribute.EXECUTION_ID, execution_id)
                        span.set_attribute(SpanAttribute.ENVIRONMENT, environment)
                        span.set_attribute(SpanAttribute.APP_ID, app_id)
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
                execution_id = str(uuid.uuid4())
                ctx = get_current()
                ctx = set_baggage("autoblocksExecutionId", execution_id, context=ctx)
                ctx = set_baggage("autoblocksEnvironment", environment, context=ctx)
                ctx = set_baggage("autoblocksAppId", app_id, context=ctx)

                tracer = trace.get_tracer("AUTOBLOCKS_TRACER")
                token = attach(ctx)
                with tracer.start_as_current_span(app_id, context=ctx) as span:
                    try:
                        span.set_attribute("autoblocksIsRoot", True)
                        span.set_attribute("autoblocksExecutionId", execution_id)
                        span.set_attribute("autoblocksEnvironment", environment)
                        span.set_attribute("autoblocksAppId", app_id)
                        span.set_attribute("autoblocksInput", serialize({"args": args, "kwargs": kwargs}))

                        result = fn(*args, **kwargs)

                        span.set_attribute("autoblocksOutput", serialize(result))
                        return result
                    finally:
                        detach(token)

            return sync_wrapper

    return decorator
