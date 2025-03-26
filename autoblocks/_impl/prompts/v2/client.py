import logging
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import httpx

from autoblocks._impl.config.constants import API_ENDPOINT_V2
from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.prompts.v2.models import Prompt
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import encode_uri_component

log = logging.getLogger(__name__)


class PromptsAPIClient:
    """Client for the Autoblocks Prompts V2 API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Prompts API client.

        Args:
            api_key: The API key to use. If None, the API key is read from the
                    environment variable AUTOBLOCKS_V2_API_KEY.
        """
        api_key = api_key or AutoblocksEnvVar.V2_API_KEY.get()
        if not api_key:
            raise ValueError(
                f"You must either pass in the API key via 'api_key' or "
                f"set the {AutoblocksEnvVar.V2_API_KEY} environment variable."
            )
        self._api_key = api_key
        self._headers = {"Authorization": f"Bearer {self._api_key}"}

    def _make_prompt_url(self, app_id: str, prompt_id: str, major_version: str, minor_version: str) -> str:
        """
        Construct the URL for a prompt API request.

        Args:
            app_id: The app ID
            prompt_id: The prompt ID
            major_version: The major version
            minor_version: The minor version

        Returns:
            The full URL
        """
        app_id = encode_uri_component(app_id)
        prompt_id = encode_uri_component(prompt_id)
        major_version = encode_uri_component(major_version)
        minor_version = encode_uri_component(minor_version)

        return f"{API_ENDPOINT_V2}/apps/{app_id}/prompts/{prompt_id}/major/{major_version}/minor/{minor_version}"

    def get_all_prompts(self) -> List[Prompt]:
        """
        Get all prompts from all apps.

        Returns:
            A list of prompt objects with their apps and major versions
        """
        url = f"{API_ENDPOINT_V2}/prompts/types"

        with httpx.Client() as client:
            response = client.get(
                url,
                headers=self._headers,
            )
            response.raise_for_status()

            # Convert the raw JSON data to Prompt objects
            return [Prompt.model_validate(prompt) for prompt in response.json()]

    def get_prompt(self, app_id: str, prompt_id: str, major_version: str, minor_version: str) -> Dict[str, Any]:
        """
        Get a specific prompt version.

        Args:
            app_id: The app ID
            prompt_id: The prompt ID
            major_version: The major version
            minor_version: The minor version

        Returns:
            The prompt data
        """
        url = self._make_prompt_url(app_id, prompt_id, major_version, minor_version)

        with httpx.Client() as client:
            response = client.get(
                url,
                headers=self._headers,
            )
            response.raise_for_status()

            # Cast the response to the correct type
            result: Dict[str, Any] = response.json()

            # Include the app_id in the result
            result["appId"] = app_id

            return result

    def get_undeployed_prompt(
        self, app_id: str, prompt_id: str, minor_version: str = REVISION_LATEST
    ) -> Dict[str, Any]:
        """
        Get an undeployed prompt.

        Args:
            app_id: The app ID
            prompt_id: The prompt ID
            minor_version: The minor version (defaults to 'latest')

        Returns:
            The undeployed prompt data
        """
        return self.get_prompt(app_id, prompt_id, REVISION_UNDEPLOYED, minor_version)

    async def get_prompt_async(
        self,
        app_id: str,
        prompt_id: str,
        major_version: str,
        minor_version: str,
        timeout: Optional[timedelta] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific prompt version asynchronously.

        Args:
            app_id: The app ID
            prompt_id: The prompt ID
            major_version: The major version
            minor_version: The minor version
            timeout: Optional timeout for the request

        Returns:
            The prompt data
        """
        url = self._make_prompt_url(app_id, prompt_id, major_version, minor_version)

        timeout_seconds = None if timeout is None else timeout.total_seconds()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._headers,
                timeout=timeout_seconds,
            )
            response.raise_for_status()

            # Cast the response to the correct type
            result: Dict[str, Any] = response.json()

            # Include the app_id in the result
            result["appId"] = app_id

            return result
