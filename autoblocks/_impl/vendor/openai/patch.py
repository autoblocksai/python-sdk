import os
import time
import uuid
from datetime import datetime
from typing import Dict
from typing import Optional

import wrapt

from autoblocks._impl.config.constants import AUTOBLOCKS_INGESTION_KEY
from autoblocks._impl.tracer import AutoblocksTracer

patch_tracer = AutoblocksTracer(
    os.environ.get(AUTOBLOCKS_INGESTION_KEY),
    properties=dict(provider="openai"),
)


def wrapper(wrapped, instance, args, kwargs):
    """
    Wrapper for OpenAI API calls. Logs the request and response to Autoblocks.

    See https://github.com/GrahamDumpleton/wrapt/blob/develop/blog/11-safely-applying-monkey-patches-in-python.md
    for more details on monkey patching via wrapt.
    """
    error = None
    response = None

    if not patch_tracer.trace_id:
        patch_tracer.set_trace_id(str(uuid.uuid4()))

    patch_tracer.send_event("ai.completion.request", properties=kwargs, timestamp=datetime.utcnow().isoformat())

    start_time = time.perf_counter()
    try:
        response = wrapped(*args, **kwargs)
    except Exception as err:
        error = err
        raise err
    finally:
        latency_ms = (time.perf_counter() - start_time) * 1000

        if error:
            patch_tracer.send_event(
                "ai.completion.error",
                properties=dict(
                    latency_ms=latency_ms,
                    error=str(error),
                ),
                timestamp=datetime.utcnow().isoformat(),
            )
        else:
            patch_tracer.send_event(
                "ai.completion.response",
                properties=dict(
                    latency_ms=latency_ms,
                    **response,
                ),
                timestamp=datetime.utcnow().isoformat(),
            )

    return response


def patch_openai(properties: Optional[Dict] = None, called=[False]):
    # Using a mutable default argument (which is only set once)
    # to track whether this function has been called before
    # to prevent patching openai multiple times.
    if called[0]:
        return

    if not os.environ.get(AUTOBLOCKS_INGESTION_KEY):
        raise ValueError(
            f"You must set the {AUTOBLOCKS_INGESTION_KEY} environment variable in order to use patch_openai."
        )

    try:
        import openai
    except ImportError:
        raise ImportError("You must have openai installed in order to use the patch_openai function.")

    if properties:
        patch_tracer.update_properties(properties)

    wrapt.wrap_function_wrapper(openai, "Completion.create", wrapper)
    wrapt.wrap_function_wrapper(openai, "ChatCompletion.create", wrapper)

    called[0] = True
