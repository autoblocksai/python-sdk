import os
import time
import uuid
from datetime import datetime
from typing import Dict
from typing import Optional

import wrapt

from autoblocks._impl.config.constants import AUTOBLOCKS_INGESTION_KEY
from autoblocks._impl.tracer import AutoblocksTracer

tracer = AutoblocksTracer(
    os.environ.get(AUTOBLOCKS_INGESTION_KEY),
    properties=dict(provider="openai"),
)


def make_timestamp():
    return datetime.utcnow().isoformat()


def wrapper(wrapped, instance, args, kwargs):
    """
    Wrapper for OpenAI API calls. Logs the request and response to Autoblocks.

    See https://github.com/GrahamDumpleton/wrapt/blob/develop/blog/11-safely-applying-monkey-patches-in-python.md
    for more details on monkey patching via wrapt.
    """
    error = None
    response = None

    if tracer.trace_id:
        # If the user has set a trace_id on the tracer via set_trace_id, don't override it.
        trace_id = None
    else:
        # Instead of using set_trace_id, this trace_id will be sent along with each send_event
        # call so that we can tell the difference between when a user sets a trace_id and when
        # we set one. In other words, we'll know the user has set a trace_id via set_trace_id
        # when tracer.trace_id is not None, since we will never set it here.
        trace_id = str(uuid.uuid4())

    tracer.send_event(
        "ai.completion.request",
        trace_id=trace_id,
        properties=kwargs,
        timestamp=make_timestamp(),
    )

    start_time = time.perf_counter()
    try:
        response = wrapped(*args, **kwargs)
    except Exception as err:
        error = err
        raise err
    finally:
        latency_ms = (time.perf_counter() - start_time) * 1000

        if error:
            tracer.send_event(
                "ai.completion.error",
                trace_id=trace_id,
                properties=dict(
                    latency_ms=latency_ms,
                    error=str(error),
                ),
                timestamp=make_timestamp(),
            )
        else:
            tracer.send_event(
                "ai.completion.response",
                trace_id=trace_id,
                properties=dict(
                    latency_ms=latency_ms,
                    **response,
                ),
                timestamp=make_timestamp(),
            )

    return response


def trace_openai(properties: Optional[Dict] = None, called=[False]) -> AutoblocksTracer:
    # Using a mutable default argument (which is only set once)
    # to track whether this function has been called before
    # to prevent patching openai multiple times.
    if called[0]:
        return tracer

    if not os.environ.get(AUTOBLOCKS_INGESTION_KEY):
        raise ValueError(
            f"You must set the {AUTOBLOCKS_INGESTION_KEY} environment variable in order to use trace_openai."
        )

    try:
        import openai
    except ImportError:
        raise ImportError("You must have openai installed in order to use the trace_openai function.")

    if properties:
        tracer.update_properties(properties)

    wrapt.wrap_function_wrapper(openai, "Completion.create", wrapper)
    wrapt.wrap_function_wrapper(openai, "ChatCompletion.create", wrapper)

    called[0] = True

    return tracer
