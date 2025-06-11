from pydantic import BaseModel

from autoblocks._impl.util import encode_uri_component
from autoblocks._impl.util import serialize_to_string


def test_encode_uri_component():
    assert encode_uri_component("hello") == "hello"
    assert encode_uri_component("hello world") == "hello%20world"
    assert encode_uri_component("hello\n!().*'") == "hello%0A!().*'"


def test_serialize_basic_types():
    assert serialize_to_string("hello") == '"hello"'
    assert serialize_to_string(123) == "123"
    assert serialize_to_string(True) == "true"
    assert serialize_to_string(None) == "null"
    assert serialize_to_string([1, 2, 3]) == "[1,2,3]"
    assert serialize_to_string({"a": 1, "b": 2}) == '{"a":1,"b":2}'


def test_serialize_pydantic_v1():
    class TestModel(BaseModel):
        name: str
        age: int

        class Config:
            json_encoders = {str: lambda v: v.upper()}

    model = TestModel(name="test", age=25)
    assert serialize_to_string(model) == '{"name":"TEST","age":25}'


def test_serialize_pydantic_v2():
    class TestModel(BaseModel):
        name: str
        age: int

        model_config = {"json_encoders": {str: lambda v: v.upper()}}

    model = TestModel(name="test", age=25)
    assert serialize_to_string(model) == '{"name":"TEST","age":25}'


def test_serialize_exception():
    try:
        raise ValueError("test error")
    except ValueError as e:
        serialized = serialize_to_string(e)
        assert "ValueError" in serialized
        assert "test error" in serialized


def test_serialize_error_case():
    class Unserializable:
        def __init__(self):
            self.self = self  # Create a circular reference

    assert serialize_to_string(Unserializable()) == "\\{\\}"  # type: ignore
