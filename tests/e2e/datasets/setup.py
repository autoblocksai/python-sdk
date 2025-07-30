import os
import uuid
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from autoblocks.api.app_client import AutoblocksAppClient
from autoblocks.datasets.models import SchemaPropertyType

# Constants for testing
APP_SLUG = "ci-app"
TEST_TIMEOUT = timedelta(seconds=300)  # 5 minutes for tests


def create_app_client() -> AutoblocksAppClient:
    """Create an app client for testing with real API calls."""
    api_key = os.environ.get("AUTOBLOCKS_V2_API_KEY")
    if not api_key:
        raise ValueError("AUTOBLOCKS_V2_API_KEY environment variable is required for tests")

    return AutoblocksAppClient(
        api_key=api_key,
        app_slug=APP_SLUG,
        timeout=TEST_TIMEOUT,
    )


def create_unique_name(prefix: str) -> str:
    """Create a unique name for a dataset."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def get_basic_schema() -> List[Dict[str, Any]]:
    """Get a basic schema for testing."""
    return [
        {
            "name": "Text Field",
            "type": SchemaPropertyType.STRING.value,
            "required": True,
        },
        {
            "name": "Number Field",
            "type": SchemaPropertyType.NUMBER.value,
            "required": False,
        },
    ]


def cleanup_dataset(client: AutoblocksAppClient, dataset_id: Optional[str]) -> None:
    """Clean up a dataset after testing."""
    if dataset_id:
        client.datasets.destroy(external_id=dataset_id)
