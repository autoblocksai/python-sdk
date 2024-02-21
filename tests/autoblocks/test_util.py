from autoblocks._impl.util import encode_uri_component


def test_encode_uri_component():
    assert encode_uri_component("hello") == "hello"
    assert encode_uri_component("hello world") == "hello%20world"
    assert encode_uri_component("hello\n!().*'") == "hello%0A!().*'"
