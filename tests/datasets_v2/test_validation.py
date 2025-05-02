import pytest
from autoblocks.datasets_v2 import validate_conversation


def test_validate_conversation_valid():
    """Test validating a valid conversation structure"""
    valid_conv = {
        "roles": ["user", "assistant"],
        "turns": [
            {
                "turn": 1,
                "messages": [
                    {"role": "user", "content": "Hello, how can you help me?"},
                    {"role": "assistant", "content": "I'm here to assist you with any questions you have."}
                ]
            },
            {
                "turn": 2,
                "messages": [
                    {"role": "user", "content": "Can you explain how to use datasets?"},
                    {"role": "assistant", "content": "Sure, I'd be happy to explain datasets."}
                ]
            }
        ]
    }
    
    result = validate_conversation(valid_conv)
    assert result["valid"] is True
    assert result["data"] is not None
    assert len(result["data"].turns) == 2
    assert result["data"].roles == ["user", "assistant"]


def test_validate_conversation_invalid_missing_roles():
    """Test validating a conversation with missing roles"""
    invalid_conv = {
        "turns": [
            {
                "turn": 1,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }
        ]
    }
    
    result = validate_conversation(invalid_conv)
    assert result["valid"] is False
    assert "must have roles" in result["message"]


def test_validate_conversation_invalid_wrong_role():
    """Test validating a conversation with an invalid role"""
    invalid_conv = {
        "roles": ["user", "assistant"],
        "turns": [
            {
                "turn": 1,
                "messages": [
                    {"role": "unknown", "content": "Hello"}
                ]
            }
        ]
    }
    
    result = validate_conversation(invalid_conv)
    assert result["valid"] is False
    assert "valid role" in result["message"]


def test_validate_conversation_invalid_turn_sequence():
    """Test validating a conversation with incorrect turn sequence"""
    invalid_conv = {
        "roles": ["user", "assistant"],
        "turns": [
            {
                "turn": 2,  # Should be 1
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }
        ]
    }
    
    result = validate_conversation(invalid_conv)
    assert result["valid"] is False
    assert "sequential" in result["message"] 