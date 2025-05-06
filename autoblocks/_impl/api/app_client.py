"""AutoblocksAppClient for app-specific operations requiring an app_slug."""

from typing import Optional
from typing import TypeVar

from autoblocks._impl.datasets_v2.client import DatasetsV2Client
from autoblocks._impl.util import AutoblocksEnvVar

T = TypeVar("T")


class AutoblocksAppClient:
    """
    API client for Autoblocks app-specific operations.

    This client is used for operations that require an app_slug, such as
    working with datasets.
    """

    def __init__(self, app_slug: str, api_key: Optional[str] = None, timeout_ms: int = 60000) -> None:
        """
        Initialize the app client.

        Args:
            app_slug: The app slug to use for all operations
            api_key: Autoblocks API key (optional, will use V2_API_KEY env var if not provided)
            timeout_ms: Request timeout in milliseconds (default: 60000)
        """
        # Get API key from env var if not provided
        self.api_key = api_key or AutoblocksEnvVar.V2_API_KEY.get()
        if not self.api_key:
            raise ValueError(
                f"You must provide an api_key or set the {AutoblocksEnvVar.V2_API_KEY} environment variable."
            )

        # Store the app_slug
        if not app_slug:
            raise ValueError("app_slug is required")

        self.app_slug = app_slug
        self.timeout_ms = timeout_ms

        # Initialize datasets client lazily
        self._datasets: Optional[DatasetsV2Client] = None

    @property
    def datasets(self) -> DatasetsV2Client:
        """
        Access to the datasets client.

        Returns:
            The datasets client with the app_slug configured
        """
        if self._datasets is None:
            # Initialize the datasets client lazily
            self._datasets = DatasetsV2Client(
                {
                    "api_key": self.api_key,
                    "app_slug": self.app_slug,
                    "timeout_ms": self.timeout_ms,
                }
            )
        assert self._datasets is not None
        return self._datasets
