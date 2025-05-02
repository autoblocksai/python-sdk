from typing import Dict, List, Optional, Union, Any, TypedDict, Tuple
import json
from .types import Conversation, ConversationMessage, ConversationTurn


class ValidationResult(TypedDict, total=False):
    valid: bool
    message: Optional[str]
    data: Optional[Conversation]


def validate_conversation(data: Any) -> ValidationResult:
    """Validates a conversation object"""
    if not isinstance(data, dict):
        return {'valid': False, 'message': 'Conversation must be an object'}

    # Validate roles
    if 'roles' not in data:
        return {'valid': False, 'message': 'Conversation must have roles'}
    
    roles = data.get('roles', [])
    if not isinstance(roles, list) or len(roles) != 2:
        return {'valid': False, 'message': 'Conversation must have exactly two roles'}
    
    # Validate each role is a non-empty string
    for role in roles:
        if not isinstance(role, str) or not role.strip():
            return {'valid': False, 'message': 'Each role must be a non-empty string'}
    
    # Validate turns
    if 'turns' not in data:
        return {'valid': False, 'message': 'Conversation must have turns'}
    
    turns = data.get('turns', [])
    if not isinstance(turns, list) or not turns:
        return {'valid': False, 'message': 'Conversation must have at least one turn'}
    
    valid_roles = set(roles)
    turn_messages = []
    
    # Validate each turn
    for i, turn in enumerate(turns):
        if not isinstance(turn, dict):
            return {'valid': False, 'message': f'Turn {i+1} must be an object'}
        
        # Validate turn number
        turn_number = turn.get('turn')
        if not isinstance(turn_number, int) or turn_number < 1:
            return {'valid': False, 'message': f'Turn {i+1} must have a valid turn number (integer ≥ 1)'}
        
        # Check expected turn order
        if turn_number != i + 1:
            return {'valid': False, 'message': 'Turn numbers must be sequential starting from 1'}
        
        # Validate messages
        messages = turn.get('messages', [])
        if not isinstance(messages, list) or not messages:
            return {'valid': False, 'message': f'Turn {i+1} must have at least one message'}
        
        # Validate each message
        turn_message_list = []
        for j, message in enumerate(messages):
            if not isinstance(message, dict):
                return {'valid': False, 'message': f'Message {j+1} in turn {i+1} must be an object'}
            
            # Validate role
            role = message.get('role', '')
            if not isinstance(role, str) or not role.strip():
                return {'valid': False, 'message': f'Message {j+1} in turn {i+1} must have a non-empty role'}
            
            # Validate role exists in defined roles
            if role not in valid_roles:
                role_list = ", ".join(valid_roles)
                return {'valid': False, 'message': f'Message must have a valid role (one of: {role_list})'}
            
            # Validate content
            content = message.get('content', '')
            if not isinstance(content, str) or not content.strip():
                return {'valid': False, 'message': f'Message {j+1} in turn {i+1} must have non-empty content'}
            
            turn_message_list.append(ConversationMessage(role=role, content=content))
        
        turn_messages.append(ConversationTurn(turn=turn_number, messages=turn_message_list))
    
    # If we get here, validation passed
    result_conversation = Conversation(
        roles=roles,
        turns=turn_messages
    )
    
    return {
        'valid': True,
        'data': result_conversation
    }


def to_json(obj: Any) -> str:
    """Convert a dataclass to JSON string"""
    if hasattr(obj, '__dict__'):
        return json.dumps(obj.__dict__)
    return json.dumps(obj) 