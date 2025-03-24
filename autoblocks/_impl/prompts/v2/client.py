import logging
from typing import Any, Dict, List, Optional

import httpx

from autoblocks._impl.config.constants import API_ENDPOINT, REVISION_LATEST
from autoblocks._impl.prompts.v2.models import Prompt
from autoblocks._impl.util import AutoblocksEnvVar, encode_uri_component

log = logging.getLogger(__name__)

class V2APIClient:
    """Client for the Autoblocks V2 API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the V2 API client.
        
        Args:
            api_key: The V2 API key to use. If None, the API key is read from the
                    environment variable AUTOBLOCKS_V2_API_KEY.
        """
        api_key = api_key or AutoblocksEnvVar.V2_API_KEY.get()
        if not api_key:
            raise ValueError(
                f"You must either pass in the API key via 'api_key' or "
                f"set the {AutoblocksEnvVar.V2_API_KEY} environment variable."
            )
        self._api_key = api_key
    
    def get_all_prompts(self) -> List[Prompt]:
        """
        Get all prompts from all apps.
        
        Returns:
            A list of prompt objects with their apps and major versions
        """
        url = f"{API_ENDPOINT}/v2/prompts/types"
        
        with httpx.Client() as client:
            response = client.get(
                url,
                headers={"Authorization": f"Bearer {self._api_key}"},
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
        app_id = encode_uri_component(app_id)
        prompt_id = encode_uri_component(prompt_id)
        major_version = encode_uri_component(major_version)
        minor_version = encode_uri_component(minor_version)
        
        url = f"{API_ENDPOINT}/v2/apps/{app_id}/prompts/{prompt_id}/major/{major_version}/minor/{minor_version}"
        
        with httpx.Client() as client:
            response = client.get(
                url,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            
            return response.json() 