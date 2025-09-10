"""App API Client."""

import logging
from datetime import timedelta

from autoblocks._impl.api.base_app_resource_client import BaseAppResourceClient
from autoblocks._impl.api.utils.serialization import deserialize_model
from autoblocks._impl.app.models import App

log = logging.getLogger(__name__)


class AppClient(BaseAppResourceClient):
    """App API Client"""

    def __init__(self, api_key: str, app_slug: str, timeout: timedelta = timedelta(seconds=60)) -> None:
        super().__init__(api_key, app_slug, timeout)

    def get_app(self) -> App:
        """
        Get the app details.

        Returns:
            App details
        """
        path = f"apps/{self.app_slug}"
        response = self._make_request("GET", path)
        return deserialize_model(App, response)


def create_app_client(api_key: str, app_slug: str, timeout: timedelta = timedelta(seconds=60)) -> AppClient:
    """
    Create an AppClient instance.

    Args:
        api_key: Autoblocks API key
        app_slug: Application slug
        timeout: Request timeout as timedelta (default: 60 seconds)

    Returns:
        AppClient instance
    """
    return AppClient(api_key=api_key, app_slug=app_slug, timeout=timeout)
