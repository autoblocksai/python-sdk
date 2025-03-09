import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from autoblocks._impl.tracer.span_processor import ExecutionIdSpanProcessor

log = logging.getLogger(__name__)


def init_auto_tracer(
    *,
    api_key: str,
    api_endpoint: Optional[str] = "https://dev-api.autoblocks.ai/v1/traces",
    is_batch_disabled: Optional[bool] = False,
) -> None:
    """
    Initialize the OpenTelemetry auto tracer.
    """
    log.debug(f"Initializing Autoblocks auto tracer with api_endpoint={api_endpoint}")
    set_global_textmap(
        CompositePropagator(
            [
                TraceContextTextMapPropagator(),
                W3CBaggagePropagator(),
            ]
        )
    )

    # Configure the OTLP exporter with your endpoint and headers.
    otlp_exporter = OTLPSpanExporter(
        endpoint=api_endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
    )

    # Create a resource to identify your service (using the semantic 'service.name' attribute)
    resource = Resource.create({"service.name": "autoblocks-auto-tracer"})

    # Create the tracer provider and add our custom and exporter span processors.
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(ExecutionIdSpanProcessor())
    if is_batch_disabled:
        provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))
    else:
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set the global tracer provider
    trace.set_tracer_provider(provider)
    log.debug("Autoblocks auto tracer initialized")
