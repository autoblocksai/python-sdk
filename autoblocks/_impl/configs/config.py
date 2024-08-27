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
from typing import TypeVar

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.configs.models import RemoteConfig
from autoblocks._impl.configs.models import RemoteConfigResponse
from autoblocks._impl.context_vars import RevisionType
from autoblocks._impl.context_vars import register_revision_usage
from autoblocks._impl.util import AnyTask
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import get_running_loop

log = logging.getLogger(__name__)

AutoblocksConfigValueType = TypeVar("AutoblocksConfigValueType")


def is_testing_context() -> bool:
    """
    Note that we check for the presence of the CLI environment
    variable and not the test case contextvars because the
    contextvars aren't set until run_test_suite is called,
    whereas a config manager might have already been imported
    and initialized by the time run_test_suite is called.
    """
    return bool(AutoblocksEnvVar.CLI_SERVER_ADDRESS.get())


def config_revisions_map() -> dict[str, str]:
    """
    The AUTOBLOCKS_OVERRIDES_CONFIG_REVISIONS environment variable is a JSON-stringified
    map of config IDs to revision IDs. This is set in CI test runs triggered
    from the UI.
    """
    if not is_testing_context():
        return {}

    config_revisions_raw = AutoblocksEnvVar.OVERRIDES_CONFIG_REVISIONS.get()
    if not config_revisions_raw:
        return {}
    return json.loads(config_revisions_raw)  # type: ignore


def make_request_url(config: RemoteConfig) -> str:
    config_id = config.id
    base = f"{API_ENDPOINT}/configs/{config_id}"
    if not isinstance(config, RemoteConfig) and (
        (config.major_version is None and config.minor_version is None)
        or config.dangerously_use_undeployed_revision is None
    ):
        raise ValueError(f"Invalid config type: {config}")

    if is_testing_context() and (revision_id := config_revisions_map().get(config_id)):
        return f"{base}/revisions/{revision_id}"

    if config.dangerously_use_undeployed_revision is not None:
        if config.dangerously_use_undeployed_revision == REVISION_LATEST:
            return f"{base}/revisions/{REVISION_LATEST}"
        else:
            return f"{base}/revisions/{config.dangerously_use_undeployed_revision}"

    if config.minor_version == REVISION_LATEST:
        return f"{base}/major/{config.major_version}/minor/{REVISION_LATEST}"

    return f"{base}/major/{config.major_version}/minor/{config.minor_version}"


def is_remote_config_refreshable(config: RemoteConfig) -> bool:
    """
    A config is refreshable if the user has specified that they want the latest deployed config
    or the latest undeployed config.
    """
    return (
        config.major_version is not None and config.minor_version == REVISION_LATEST
    ) or config.dangerously_use_undeployed_revision == REVISION_LATEST


async def get_remote_config(config: RemoteConfig, timeout: timedelta, api_key: str) -> RemoteConfigResponse:
    resp = await global_state.http_client().get(
        make_request_url(config=config),
        timeout=timeout.total_seconds(),
        headers={"Authorization": f"Bearer {api_key}"},
    )
    resp.raise_for_status()
    return RemoteConfigResponse.model_validate(resp.json())


class AutoblocksConfig(
    abc.ABC,
    Generic[AutoblocksConfigValueType],
):
    _value: AutoblocksConfigValueType
    _remote_config_id: Optional[str] = None
    _remote_config_revision_id: Optional[str] = None
    _is_stopped_refreshing: bool = False

    def __init__(self, value: AutoblocksConfigValueType) -> None:
        self._value = value

    async def _refresh_loop(
        self,
        config: RemoteConfig,
        refresh_interval: timedelta,
        refresh_timeout: timedelta,
        api_key: str,
        parser: Callable[[Dict[str, Any]], AutoblocksConfigValueType],
    ) -> None:
        """
        Refreshes the latest version of the config every `refresh_interval` seconds.

        This isn't exactly "every n seconds" but more "run and then wait n seconds",
        which will cause it to drift each run by the time it takes to run the refresh,
        but I think that is ok in this scenario.
        """
        while not self._is_stopped_refreshing:
            await asyncio.sleep(refresh_interval.total_seconds())

            try:
                if not self._is_stopped_refreshing:
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
        parser: Callable[[Dict[str, Any]], AutoblocksConfigValueType],
    ) -> None:
        """
        Loads the remote config from Autoblocks and sets the value of this config
        based on the result.

        If the parser is specified, the value will be parsed using the parser.
        """
        remote_config = await get_remote_config(config, timeout=timeout, api_key=api_key)
        try:
            obj = {}
            for prop in remote_config.properties:
                obj[prop.id] = prop.value
            parsed = parser(obj)
            if parsed is not None:
                self._value = parsed
                self._remote_config_id = remote_config.id
                self._remote_config_revision_id = remote_config.revision_id
        except Exception as err:
            log.error(f"Failed to parse config '{config.id}': {err}", exc_info=True)
            raise err

    def _activate_from_remote_unsafe(
        self,
        config: RemoteConfig,
        refresh_interval: timedelta,
        refresh_timeout: timedelta,
        activate_timeout: timedelta,
        parser: Callable[[Dict[str, Any]], AutoblocksConfigValueType],
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

    def activate_from_remote(
        self,
        config: RemoteConfig,
        parser: Callable[[Dict[str, Any]], AutoblocksConfigValueType],
        api_key: Optional[str] = None,
        refresh_interval: timedelta = timedelta(seconds=10),
        refresh_timeout: timedelta = timedelta(seconds=30),
        activate_timeout: timedelta = timedelta(seconds=30),
    ) -> None:
        """
        Activate a remote config from Autoblocks and optionally refresh it every `refresh_interval` seconds.
        """
        try:
            log.info(f"Activating remote config '{config.id}'")
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

    def stop_refreshing(self) -> None:
        """
        Stops the config from automatically refreshing.
        """
        log.info(f"Stopping automatic refreshing for config '{self._remote_config_id}'.")
        self._is_stopped_refreshing = True

    @property
    def value(self) -> AutoblocksConfigValueType:
        if is_testing_context() and self._remote_config_id and self._remote_config_revision_id:
            register_revision_usage(
                entity_id=self._remote_config_id,
                entity_type=RevisionType.CONFIG,
                revision_id=self._remote_config_revision_id,
            )
        return self._value
