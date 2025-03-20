import logging
from datetime import timedelta
from typing import Optional

import httpx

from autoblocks._impl.api.v2.models import Prompt
from autoblocks._impl.config.constants import V2_API_ENDPOINT
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import encode_uri_component

log = logging.getLogger(__name__)


class AutoblocksAPIClient:
    """Client for the Autoblocks V2 API."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        timeout: timedelta = timedelta(seconds=10)
    ) -> None:
        """Initialize the client with an API key.
        
        Args:
            api_key: The API key to use. If None, will try to read from environment.
            timeout: Default timeout for requests.
        """
        api_key = api_key or AutoblocksEnvVar.V2_API_KEY.get()
        if not api_key:
            raise ValueError(
                f"You must provide an api_key or set the {AutoblocksEnvVar.V2_API_KEY} environment variable."
            )
        self._client = httpx.Client(
            base_url=V2_API_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout.total_seconds(),
        )
        
    def get_prompt(
        self, 
        app_id: str,
        prompt_id: str, 
        major_version: str, 
        minor_version: str,
        timeout: Optional[timedelta] = None,
    ) -> Prompt:
        """Get a prompt from the V2 API.
        
        Args:
            app_id: The app ID containing the prompt.
            prompt_id: The ID of the prompt to get.
            major_version: The major version of the prompt.
            minor_version: The minor version of the prompt.
            timeout: Request timeout. If None, uses the client's default.
            
        Returns:
            The prompt object.
        """
        url = f"/apps/{encode_uri_component(app_id)}/prompts/{encode_uri_component(prompt_id)}/major/{encode_uri_component(major_version)}/minor/{encode_uri_component(minor_version)}"
        timeout_seconds = timeout.total_seconds() if timeout else None
        req = self._client.get(url, timeout=timeout_seconds)
        req.raise_for_status()
        return Prompt.model_validate(req.json()) 