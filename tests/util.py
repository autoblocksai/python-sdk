import json
from typing import Dict


def make_expected_body(data: Dict) -> bytes:
    """
    For use in `match_content` in httpx_mock.add_response:

    https://github.com/Colin-b/pytest_httpx#matching-on-http-body-1
    """
    return json.dumps(data).encode()
