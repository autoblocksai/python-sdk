import os
from unittest import mock

import pydantic

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks.configs.config import AutoblocksConfig
from autoblocks.configs.models import LatestRemoteConfig


class MyConfigValue(pydantic.BaseModel):
    my_val: str


class MyConfig(AutoblocksConfig[MyConfigValue]):
    pass


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
    },
)
def test_activates_remote_config(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/configs/my-config-id/versions/latest",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="my-config-id",
            version="1",
            value=dict(
                my_val="val-from-remote",
            ),
        ),
    )

    config = MyConfig(
        value=MyConfigValue(my_val="initial-val"),
    )
    config.activate_from_remote(
        config=LatestRemoteConfig(id="my-config-id", latest=True), parser=MyConfigValue.model_validate
    )

    assert config.value == MyConfigValue(my_val="val-from-remote")
