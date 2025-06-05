"""Scenarios API models."""

from enum import Enum
from typing import List

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class MessageRole(str, Enum):
    """Message role enum."""

    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    """Message model for conversation history."""

    role: MessageRole
    content: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ScenarioItem(BaseModel):
    """Scenario item with ID only."""

    id: str

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class ScenariosResponse(BaseModel):
    """Response model for listing scenarios."""

    scenarios: List[ScenarioItem]

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class GenerateMessageRequest(BaseModel):
    """Request model for generating a message."""

    messages: List[Message]

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class GenerateMessageResponse(BaseModel):
    """Response model for generating a message."""

    message: str
    is_final_message: bool = Field(alias="isFinalMessage")

    model_config = ConfigDict(populate_by_name=True, extra="allow")
