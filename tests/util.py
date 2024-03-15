import json
from typing import Any
from typing import Dict
from typing import Optional


def make_expected_body(data: Dict) -> bytes:
    """
    For use in `match_content` in httpx_mock.add_response:

    https://github.com/Colin-b/pytest_httpx#matching-on-http-body-1
    """
    return json.dumps(data).encode()


def decode_request_body(req) -> Dict:
    return json.loads(req.content.decode())


MOCK_CLI_SERVER_ADDRESS = "http://localhost:8080"


def expect_cli_post_request(
    httpx_mock,
    path: str,
    body: Optional[dict[str, Any]],
):
    httpx_mock.add_response(
        url=f"{MOCK_CLI_SERVER_ADDRESS}{path}",
        method="POST",
        status_code=200,
        match_content=make_expected_body(body) if body is not None else None,
    )
