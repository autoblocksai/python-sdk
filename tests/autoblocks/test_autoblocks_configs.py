import json
import os
from unittest import mock

import pydantic

from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks.configs.config import AutoblocksConfig
from autoblocks.configs.models import DangerouslyUseUndeployedRemoteConfig
from autoblocks.configs.models import DangerouslyUseUndeployedWithRevision
from autoblocks.configs.models import LatestDangerouslyUseUndeployed
from autoblocks.configs.models import LatestRemoteConfig
from autoblocks.configs.models import RemoteConfigWithVersion
from tests.util import MOCK_CLI_SERVER_ADDRESS


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
def test_gracefully_handles_parser_error(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/configs/my-config-id/versions/latest",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="my-config-id",
            version="1",
            value=dict(
                random_val="val-from-remote",
            ),
        ),
    )

    config = MyConfig(
        value=MyConfigValue(my_val="initial-val"),
    )
    config.activate_from_remote(config=LatestRemoteConfig(id="my-config-id"), parser=MyConfigValue.model_validate)

    assert config.value == MyConfigValue(my_val="initial-val")


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
    },
)
def test_activates_latest(httpx_mock):
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
    config.activate_from_remote(config=LatestRemoteConfig(id="my-config-id"), parser=MyConfigValue.model_validate)

    assert config.value == MyConfigValue(my_val="val-from-remote")


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
    },
)
def test_activates_specific_version(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/configs/my-config-id/versions/1",
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
        config=RemoteConfigWithVersion(id="my-config-id", version="1"), parser=MyConfigValue.model_validate
    )

    assert config.value == MyConfigValue(my_val="val-from-remote")


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
    },
)
def test_activates_undeployed_latest(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/configs/my-config-id/revisions/latest",
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
        config=DangerouslyUseUndeployedRemoteConfig(
            id="my-config-id", dangerously_use_undeployed=LatestDangerouslyUseUndeployed(latest=True)
        ),
        parser=MyConfigValue.model_validate,
    )

    assert config.value == MyConfigValue(my_val="val-from-remote")


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
    },
)
def test_activates_undeployed_revision_id(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/configs/my-config-id/revisions/my-revision-id",
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
        config=DangerouslyUseUndeployedRemoteConfig(
            id="my-config-id",
            dangerously_use_undeployed=DangerouslyUseUndeployedWithRevision(revision_id="my-revision-id"),
        ),
        parser=MyConfigValue.model_validate,
    )

    assert config.value == MyConfigValue(my_val="val-from-remote")


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        "AUTOBLOCKS_CLI_SERVER_ADDRESS": MOCK_CLI_SERVER_ADDRESS,
        "AUTOBLOCKS_CONFIG_REVISIONS": json.dumps({"my-config-id": "mock-revision-id"}),
    },
)
def test_activates_revision_id_override(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/configs/my-config-id/revisions/mock-revision-id",
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
        config=DangerouslyUseUndeployedRemoteConfig(
            id="my-config-id",
            dangerously_use_undeployed=DangerouslyUseUndeployedWithRevision(revision_id="my-revision-id"),
        ),
        parser=MyConfigValue.model_validate,
    )

    assert config.value == MyConfigValue(my_val="val-from-remote")


@mock.patch.dict(
    os.environ,
    {
        "AUTOBLOCKS_API_KEY": "mock-api-key",
        # Note that AUTOBLOCKS_CLI_SERVER_ADDRESS is not set
        "AUTOBLOCKS_CONFIG_REVISIONS": json.dumps({"my-config-id": "mock-revision-id"}),
    },
)
def test_ignores_revision_id_if_not_in_test_run_context(httpx_mock):
    httpx_mock.add_response(
        url=f"{API_ENDPOINT}/configs/my-config-id/versions/latest",
        method="GET",
        match_headers={"Authorization": "Bearer mock-api-key"},
        json=dict(
            id="my-config-id",
            version="1",
            value=dict(
                my_val="val-from-remote-latest",
            ),
        ),
    )

    config = MyConfig(
        value=MyConfigValue(my_val="initial-val"),
    )
    config.activate_from_remote(config=LatestRemoteConfig(id="my-config-id"), parser=MyConfigValue.model_validate)

    assert config.value == MyConfigValue(my_val="val-from-remote-latest")
    # ensure we only made one call to get latest
    assert len(httpx_mock.get_requests()) == 1
