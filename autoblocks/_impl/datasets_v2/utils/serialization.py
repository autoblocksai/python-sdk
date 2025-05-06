"""Serialization utilities for Datasets V2 API."""
import json
from typing import Any, Dict, List, Optional, TypeVar, Type, Union, TypeAlias

from pydantic import BaseModel

# Type aliases for cleaner code
JsonDict: TypeAlias = Dict[str, Any]
JsonList: TypeAlias = List[Any]
JsonValue: TypeAlias = Union[str, int, float, bool, None, JsonDict, JsonList]

T = TypeVar('T', bound=BaseModel)


def serialize_model(model: BaseModel) -> JsonDict:
    """
    Serialize a Pydantic model to a dictionary with camelCase keys.
    
    Args:
        model: The Pydantic model to serialize
        
    Returns:
        A dictionary representation with camelCase keys
    """
    if not isinstance(model, BaseModel):
        raise TypeError(f"Expected Pydantic model, got {type(model).__name__}")
    
    return model.model_dump(by_alias=True, exclude_none=True)


def deserialize_model(data: JsonDict, model_class: Type[T]) -> T:
    """
    Deserialize a dictionary into a Pydantic model.
    
    Args:
        data: The dictionary data to deserialize
        model_class: The Pydantic model class to create
        
    Returns:
        An instance of the specified model class
    """
    return model_class.model_validate(data)


def deserialize_model_list(data: List[JsonDict], model_class: Type[T]) -> List[T]:
    """
    Deserialize a list of dictionaries into a list of Pydantic models.
    
    Args:
        data: The list of dictionaries to deserialize
        model_class: The Pydantic model class to create
        
    Returns:
        A list of instances of the specified model class
    """
    return [deserialize_model(item, model_class) for item in data] 