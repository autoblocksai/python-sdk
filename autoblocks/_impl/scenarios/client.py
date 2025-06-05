"""Scenarios API Client."""

import logging
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List

from autoblocks._impl.api.base_app_resource_client import BaseAppResourceClient
from autoblocks._impl.api.exceptions import ValidationError
from autoblocks._impl.api.utils.serialization import deserialize_model
from autoblocks._impl.api.utils.serialization import serialize_model
from autoblocks._impl.scenarios.models import GenerateMessageResponse
from autoblocks._impl.scenarios.models import Message
from autoblocks._impl.scenarios.models import ScenarioItem
from autoblocks._impl.scenarios.models import ScenariosResponse

log = logging.getLogger(__name__)


class ScenariosClient(BaseAppResourceClient):
    """Scenarios API Client"""

    def __init__(self, api_key: str, app_slug: str, timeout: timedelta = timedelta(seconds=60)) -> None:
        super().__init__(api_key, app_slug, timeout)

    def list_scenarios(self) -> List[ScenarioItem]:
        """
        List all scenario IDs in the app.

        Returns:
            List of scenario items
        """
        path = self._build_app_path("scenarios")
        response = self._make_request("GET", path)
        scenarios_response = deserialize_model(ScenariosResponse, response)
        return scenarios_response.scenarios

    def generate_message(self, *, scenario_id: str, messages: List[Message]) -> GenerateMessageResponse:
        """
        Generate a message for a scenario based on conversation history.

        Args:
            scenario_id: Scenario ID (required)
            messages: List of conversation messages (required)

        Returns:
            Generated message response

        Raises:
            ValidationError: If scenario_id is not provided or messages list is empty
        """
        if not scenario_id:
            raise ValidationError("Scenario ID is required")

        # Prepare data payload
        data: Dict[str, Any] = {"messages": [serialize_model(message) for message in messages]}

        path = self._build_app_path("scenarios", scenario_id, "generate-message")
        response = self._make_request("POST", path, data)
        return deserialize_model(GenerateMessageResponse, response)


def create_scenarios_client(api_key: str, app_slug: str, timeout: timedelta = timedelta(seconds=60)) -> ScenariosClient:
    """
    Create a ScenariosClient instance.

    Args:
        api_key: Autoblocks API key
        app_slug: Application slug
        timeout: Request timeout as timedelta (default: 60 seconds)

    Returns:
        ScenariosClient instance
    """
    return ScenariosClient(api_key=api_key, app_slug=app_slug, timeout=timeout)
