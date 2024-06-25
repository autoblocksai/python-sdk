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
    status_code: int = 200,
) -> None:
    httpx_mock.add_response(
        url=f"{MOCK_CLI_SERVER_ADDRESS}{path}",
        method="POST",
        status_code=status_code,
        match_json=body,
    )


def expect_openai_post_request(
    httpx_mock: Any,
    response_message_content: str,
    status_code: int = 200,
) -> None:
    httpx_mock.add_response(
        url="https://api.openai.com/v1/chat/completions",
        method="POST",
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": response_message_content,
                    },
                },
            ],
        },
        status_code=status_code,
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
