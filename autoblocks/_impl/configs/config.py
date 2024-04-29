import abc
import asyncio
import json
import logging
from datetime import timedelta
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generic
from typing import Optional
from typing import Type
from typing import TypeVar

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.configs.models import DangerouslyUseUndeployedRemoteConfig
from autoblocks._impl.configs.models import DangerouslyUseUndeployedWithRevision
from autoblocks._impl.configs.models import LatestDangerouslyUseUndeployed
from autoblocks._impl.configs.models import LatestRemoteConfig
from autoblocks._impl.configs.models import RemoteConfig
from autoblocks._impl.configs.models import RemoteConfigResponse
from autoblocks._impl.configs.models import RemoteConfigWithVersion
from autoblocks._impl.util import AnyTask
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import get_running_loop

log = logging.getLogger(__name__)

AutoblocksConfigValue = TypeVar("AutoblocksConfigValue")


def is_testing_context() -> bool:
    """
    Note that we check for the presence of the CLI environment
    variable and not the test case contextvars because the
    contextvars aren't set until run_test_suite is called,
    whereas a prompt manager might have already been imported
    and initialized by the time run_test_suite is called.
    """
    return bool(AutoblocksEnvVar.CLI_SERVER_ADDRESS.get())


def config_revisions_map() -> dict[str, str]:
    """
    The AUTOBLOCKS_CONFIG_REVISIONS environment variable is a JSON-stringified
    map of config IDs to revision IDs. This is set in CI test runs triggered
    from the UI.
    """
    if not is_testing_context():
        return {}

    config_revisions_raw = AutoblocksEnvVar.CONFIG_REVISIONS.get()
    if not config_revisions_raw:
        return {}
    return json.loads(config_revisions_raw)  # type: ignore


def make_request_url(config: RemoteConfig) -> str:
    config_id = config.id
    base = f"{API_ENDPOINT}/configs/{config_id}"
    revision_id = config_revisions_map().get(config_id)
    if revision_id and is_testing_context():
        return f"{base}/revisions/{revision_id}"
    if isinstance(config, LatestRemoteConfig):
        return f"{base}/versions/latest"
    elif isinstance(config, RemoteConfigWithVersion):
        return f"{base}/versions/{config.version}"
    elif isinstance(config, DangerouslyUseUndeployedRemoteConfig) and isinstance(
        config.dangerouslyUseUndeployed, DangerouslyUseUndeployedWithRevision
    ):
        if isinstance(config.dangerouslyUseUndeployed, DangerouslyUseUndeployedWithRevision):
            return f"{base}/revisions/{config.dangerouslyUseUndeployed.revisionId}"
        else:
            return f"{base}/revisions/latest"

    raise ValueError(f"Invalid config type: {config}")


def is_remote_config_refreshable(config: RemoteConfig) -> bool:
    """
    A config is refreshable if the user has specified that they want the latest deployed config
    or the latest undeployed config.
    """
    return isinstance(config, LatestRemoteConfig) or (
        isinstance(config, DangerouslyUseUndeployedRemoteConfig)
        and isinstance(config.dangerouslyUseUndeployed, LatestDangerouslyUseUndeployed)
    )


async def get_remote_config(config: RemoteConfig, timeout: timedelta, api_key: str) -> RemoteConfigResponse:
    resp = await global_state.http_client().get(
        make_request_url(config=config),
        timeout=timeout.total_seconds(),
        headers={"Authorization": f"Bearer {api_key}"},
    )
    resp.raise_for_status()
    return RemoteConfigResponse(
        id=resp.json().get("id"),
        version=resp.json().get("version"),
        value=resp.json().get("value"),
    )


class AutoblocksConfig(
    abc.ABC,
    Generic[AutoblocksConfigValue],
):
    _value: Type[AutoblocksConfigValue]

    def __init__(self, value: Type[AutoblocksConfigValue]) -> None:
        self._value = value

    async def _refresh_loop(
        self,
        config: RemoteConfig,
        refresh_interval: timedelta,
        refresh_timeout: timedelta,
        api_key: str,
        parser: Optional[Callable[[Dict[str, Any]], Type[AutoblocksConfigValue]]],
    ) -> None:
        """
        Refreshes the latest version of the config every `refresh_interval` seconds.

        This isn't exactly "every n seconds" but more "run and then wait n seconds",
        which will cause it to drift each run by the time it takes to run the refresh,
        but I think that is ok in this scenario.
        """
        while True:
            await asyncio.sleep(refresh_interval.total_seconds())

            try:
                await self._load_and_set_remote_config(
                    config=config, api_key=api_key, timeout=refresh_timeout, parser=parser
                )
            except Exception as err:
                log.warning(f"Failed to refresh config '{config.id}': {err}")

    async def _load_and_set_remote_config(
        self,
        config: RemoteConfig,
        api_key: str,
        timeout: timedelta,
        parser: Optional[Callable[[Dict[str, Any]], Type[AutoblocksConfigValue]]],
    ) -> None:
        """
        Loads the remote config from Autoblocks and sets the value of this config
        based on the result.

        If the parser is specified, the value will be parsed using the parser.
        """
        remote_config = await get_remote_config(config, timeout=timeout, api_key=api_key)
        if parser:
            try:
                parsed = parser(remote_config.value)
                if parsed is not None:
                    self._value = parsed
            except Exception as e:
                raise Exception(f"Failed to parse config '{config.id}': {e}")
        else:
            # if no parser is specified we assume the value is already in the correct type
            self._value = remote_config.value  # type: ignore

    def _activate_from_remote_unsafe(
        self,
        config: RemoteConfig,
        refresh_interval: timedelta,
        refresh_timeout: timedelta,
        activate_timeout: timedelta,
        parser: Optional[Callable[[Dict[str, Any]], Type[AutoblocksConfigValue]]],
        api_key: Optional[str] = None,
    ) -> None:
        api_key = api_key or AutoblocksEnvVar.API_KEY.get()
        if not api_key:
            raise ValueError(
                f"You must either pass in the API key via 'api_key' or "
                f"set the {AutoblocksEnvVar.API_KEY} environment variable."
            )

        global_state.init()
        task: AnyTask
        if running_loop := get_running_loop():
            # If we're already in a running loop, execute the task on that loop
            task = running_loop.create_task(
                self._load_and_set_remote_config(
                    config=config, api_key=api_key, timeout=activate_timeout, parser=parser
                ),
            )
        else:
            # Otherwise, send the task to our background loop
            task = asyncio.run_coroutine_threadsafe(
                self._load_and_set_remote_config(
                    config=config, api_key=api_key, timeout=activate_timeout, parser=parser
                ),
                global_state.event_loop(),
            )

        # Wait for config to be initialized
        task.result()

        # we do not refresh the config if we are in a testing context
        if is_remote_config_refreshable(config) and not is_testing_context():
            if running_loop := get_running_loop():
                running_loop.create_task(
                    self._refresh_loop(
                        config=config,
                        api_key=api_key,
                        refresh_interval=refresh_interval,
                        refresh_timeout=refresh_timeout,
                        parser=parser,
                    )
                )
            else:
                asyncio.run_coroutine_threadsafe(
                    self._refresh_loop(
                        config=config,
                        api_key=api_key,
                        refresh_interval=refresh_interval,
                        refresh_timeout=refresh_timeout,
                        parser=parser,
                    ),
                    global_state.event_loop(),
                )

    async def activate_from_remote(
        self,
        config: RemoteConfig,
        parser: Optional[Callable[[Dict[str, Any]], Type[AutoblocksConfigValue]]],
        api_key: Optional[str] = None,
        refresh_interval: timedelta = timedelta(seconds=10),
        refresh_timeout: timedelta = timedelta(seconds=30),
        activate_timeout: timedelta = timedelta(seconds=30),
    ) -> None:
        """
        Activate a remote config from Autoblocks and optionally refresh it every `refresh_interval` seconds.
        """
        try:
            self._activate_from_remote_unsafe(
                config=config,
                api_key=api_key,
                refresh_interval=refresh_interval,
                refresh_timeout=refresh_timeout,
                activate_timeout=activate_timeout,
                parser=parser,
            )
        except Exception as err:
            log.error(f"Failed to activate remote config '{config.id}': {err}")

    @property
    def value(self) -> Type[AutoblocksConfigValue]:
        return self._value
