"""AutoblocksAppClient for app-specific operations requiring an app_slug."""

from datetime import timedelta
from typing import Optional

from autoblocks._impl.datasets.client import DatasetsClient
from autoblocks._impl.util import AutoblocksEnvVar


class AutoblocksAppClient:
    """
    API client for Autoblocks app-specific operations.

    This client is used for operations that require an app_slug, such as
    working with datasets.
    """

    def __init__(
        self, app_slug: str, api_key: Optional[str] = None, timeout: timedelta = timedelta(seconds=10)
    ) -> None:
        """
        Initialize the app client.

        Args:
            app_slug: The app slug to use for all operations
            api_key: Autoblocks API key (optional, will use V2_API_KEY env var if not provided)
            timeout: Request timeout as a timedelta (default: 10 seconds)
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
        self.timeout = timeout

        # Initialize datasets client lazily
        self._datasets = DatasetsClient(api_key=self.api_key, app_slug=self.app_slug, timeout=timeout)

    @property
    def datasets(self) -> DatasetsClient:
        """
        Access to the datasets client.

        Returns:
            The datasets client with the app_slug configured
        """
        return self._datasets
