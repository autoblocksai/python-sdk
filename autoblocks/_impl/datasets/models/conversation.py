"""Conversation models for Datasets API."""

from typing import List

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import field_validator
from pydantic import model_validator


class ConversationMessage(BaseModel):
    """
    Represents a single message in a conversation turn.
    """

    role: str
    content: str

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role is non-empty"""
        if not v.strip():
            raise ValueError("Role cannot be empty")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is non-empty"""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v


class ConversationTurn(BaseModel):
    """
    Represents a single turn in a conversation, consisting of one or more messages.
    """

    turn: int
    messages: List[ConversationMessage]

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @field_validator("turn")
    @classmethod
    def validate_turn(cls, v: int) -> int:
        """Validate turn number is positive"""
        if v < 1:
            raise ValueError("Turn number must be positive")
        return v

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[ConversationMessage]) -> List[ConversationMessage]:
        """Validate messages list is not empty"""
        if not v:
            raise ValueError("Messages list cannot be empty")
        return v


class Conversation(BaseModel):
    """
    Represents a complete conversation with roles and turns.
    """

    roles: List[str]
    turns: List[ConversationTurn]

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, v: List[str]) -> List[str]:
        """Validate roles list has exactly two roles"""
        if len(v) != 2:
            raise ValueError("Conversation must have exactly two roles")

        # Validate each role is a non-empty string
        for role in v:
            if not isinstance(role, str) or not role.strip():
                raise ValueError("Each role must be a non-empty string")

        return v

    @field_validator("turns")
    @classmethod
    def validate_turns(cls, v: List[ConversationTurn]) -> List[ConversationTurn]:
        """Validate turns list is not empty"""
        if not v:
            raise ValueError("Turns list cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_turn_sequence(self) -> "Conversation":
        """Validate turns are sequential and all messages have valid roles"""
        # Check that turns are sequential
        expected_turn_number = 1
        for turn in self.turns:
            if turn.turn != expected_turn_number:
                raise ValueError(f"Expected turn {expected_turn_number}, got {turn.turn}")
            expected_turn_number += 1

        # Check that all messages have valid roles
        valid_roles = set(self.roles)
        for turn in self.turns:
            for message in turn.messages:
                if message.role not in valid_roles:
                    role_list = ", ".join(valid_roles)
                    raise ValueError(f"Invalid role '{message.role}'. Expected one of: {role_list}")

        return self
