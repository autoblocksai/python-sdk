import dataclasses
import hashlib
from typing import Any

import orjson

from autoblocks._impl.testing.models import BaseTestCase


def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def orjson_default(o: Any) -> Any:
    if hasattr(o, "model_dump_json") and callable(o.model_dump_json):
        # pydantic v2
        return orjson.loads(o.model_dump_json())
    elif hasattr(o, "json") and callable(o.json):
        # pydantic v1
        return orjson.loads(o.json())
    raise TypeError


def serialize(x: Any) -> Any:
    return orjson.loads(orjson.dumps(x, default=orjson_default))


def serialize_test_case(test_case: BaseTestCase) -> Any:
    # See https://docs.python.org/3/library/dataclasses.html#dataclasses.is_dataclass:
    # isinstance(test_case, type) checks test_case is an instance and not a type
    if dataclasses.is_dataclass(test_case) and not isinstance(test_case, type):
        serialized: dict[Any, Any] = {}
        for k, v in dataclasses.asdict(test_case).items():
            try:
                serialized[k] = serialize(v)
            except Exception:
                # Skip over non-serializable test case attributes
                pass
        return serialized

    return serialize(test_case)
