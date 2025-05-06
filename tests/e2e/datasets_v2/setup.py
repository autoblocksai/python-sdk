import os
import uuid
from typing import List
from typing import Optional

from autoblocks._impl.util import cuid_generator
from autoblocks.datasets_v2.client import DatasetsV2Client
from autoblocks.datasets_v2.client import create_datasets_v2_client
from autoblocks.datasets_v2.models import NumberProperty
from autoblocks.datasets_v2.models import SchemaProperty
from autoblocks.datasets_v2.models import SchemaPropertyType
from autoblocks.datasets_v2.models import StringProperty

# Constants for testing
APP_SLUG = "ci-app"
TEST_TIMEOUT = 60000  # 60 seconds


def create_test_client() -> DatasetsV2Client:
    """Create a client for testing with real API calls."""
    api_key = os.environ.get("AUTOBLOCKS_V2_API_KEY")
    if not api_key:
        raise ValueError("AUTOBLOCKS_V2_API_KEY environment variable is required for tests")

    return create_datasets_v2_client(
        api_key=api_key,
        app_slug=APP_SLUG,
        timeout_ms=TEST_TIMEOUT,
    )


def create_unique_name(prefix: str) -> str:
    """Create a unique name for a dataset."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def get_basic_schema() -> List[SchemaProperty]:
    """Get a basic schema for testing."""
    return [
        StringProperty(
            id=cuid_generator(),
            name="Text Field",
            type=SchemaPropertyType.STRING,
            required=True,
        ),
        NumberProperty(
            id=cuid_generator(),
            name="Number Field",
            type=SchemaPropertyType.NUMBER,
            required=False,
        ),
    ]


def cleanup_dataset(client: DatasetsV2Client, dataset_id: Optional[str]) -> None:
    """Clean up a dataset after testing."""
    if dataset_id:
        client.destroy(dataset_id)
