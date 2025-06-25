from autoblocks._impl.util import AutoblocksEnvVar

API_ENDPOINT = "https://api.autoblocks.ai"
API_ENDPOINT_V2 = AutoblocksEnvVar.V2_API_ENDPOINT.get() or "https://api-v2.autoblocks.ai"
INGESTION_ENDPOINT = "https://ingest-event.autoblocks.ai"
REVISION_LATEST = "latest"
REVISION_UNDEPLOYED = "undeployed"
