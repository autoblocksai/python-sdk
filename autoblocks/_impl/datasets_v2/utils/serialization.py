"""Serialization utilities for Datasets V2 API."""

from typing import Any
from typing import Dict
from typing import List
from typing import Type
from typing import TypeAlias
from typing import TypeVar
from typing import Union

from pydantic import BaseModel

# Type aliases for cleaner code
JsonDict: TypeAlias = Dict[str, Any]
JsonList: TypeAlias = List[Any]
JsonValue: TypeAlias = Union[str, int, float, bool, None, JsonDict, JsonList]

T = TypeVar("T", bound=BaseModel)


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

    # Serialize the model with aliases and without None values
    result = model.model_dump(by_alias=True, exclude_none=True)

    # Convert enum values to strings if needed
    result = _process_enum_values(result)

    return result


def _process_enum_values(data: Any) -> Any:
    """
    Process enum values in serialized data, converting them to their string value.

    Args:
        data: The data to process

    Returns:
        Processed data with enum values converted to strings
    """
    if isinstance(data, dict):
        return {k: _process_enum_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_process_enum_values(item) for item in data]
    elif hasattr(data, "value"):  # Check if it's an enum
        return data.value
    else:
        return data


def deserialize_model(data: JsonDict, model_class: Type[T]) -> T:
    """
    Deserialize a dictionary into a Pydantic model.

    Args:
        data: The dictionary data to deserialize
        model_class: The Pydantic model class to create

    Returns:
        An instance of the specified model class
    """
    if not data:
        # Handle empty responses with default values
        try:
            return model_class.model_validate({})
        except Exception as e:
            raise ValueError(f"Cannot create {model_class.__name__} with empty data: {str(e)}")

    try:
        return model_class.model_validate(data)
    except Exception as e:
        raise ValueError(f"Failed to deserialize {model_class.__name__}: {str(e)}")


def deserialize_model_list(data: List[JsonDict], model_class: Type[T]) -> List[T]:
    """
    Deserialize a list of dictionaries into a list of Pydantic models.

    Args:
        data: The list of dictionaries to deserialize
        model_class: The Pydantic model class to create

    Returns:
        A list of instances of the specified model class
    """
    if not data:
        return []

    return [deserialize_model(item, model_class) for item in data]
