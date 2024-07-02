import json
from typing import Any
from typing import Optional


def make_expected_body(data: dict[str, Any]) -> bytes:
    """
    For use in `match_content` in httpx_mock.add_response:

    https://github.com/Colin-b/pytest_httpx#matching-on-http-body-1
    """
    return json.dumps(data).encode()


def decode_request_body(req: Any) -> Any:
    return json.loads(req.content.decode())


MOCK_CLI_SERVER_ADDRESS = "http://localhost:8080"


def expect_cli_post_request(
    httpx_mock: Any,
    path: str,
    body: Optional[dict[str, Any]],
    json: Optional[dict[str, Any]] = None,
    status_code: int = 200,
) -> None:
    httpx_mock.add_response(
        url=f"{MOCK_CLI_SERVER_ADDRESS}{path}",
        method="POST",
        status_code=status_code,
        match_json=body,
        json=json,
    )


class AnyNumber(float):
    """
    Like mock.ANY but checks if the value is any number.
    """

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, (int, float)) and not isinstance(other, bool)

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return "<AnyNumber>"


ANY_NUMBER = AnyNumber()


class AnyString(str):
    """
    Like mock.ANY but checks if the value is any string.
    """

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, str)

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return "<AnyString>"


ANY_STRING = AnyString()
