import abc
import asyncio
import contextlib
import json
import logging
from datetime import timedelta
from enum import Enum
from http import HTTPStatus
from typing import Any
from typing import ContextManager
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT
from autoblocks._impl.prompts.constants import LATEST
from autoblocks._impl.prompts.constants import UNDEPLOYED
from autoblocks._impl.prompts.context import PromptExecutionContext
from autoblocks._impl.prompts.error import IncompatiblePromptSnapshotError
from autoblocks._impl.prompts.models import Prompt
from autoblocks._impl.prompts.models import PromptMinorVersion
from autoblocks._impl.prompts.models import WeightedMinorVersion
from autoblocks._impl.util import AnyTask
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import encode_uri_component
from autoblocks._impl.util import get_running_loop

log = logging.getLogger(__name__)

ExecutionContextType = TypeVar("ExecutionContextType", bound=PromptExecutionContext[Any, Any])
MinorVersionEnumType = TypeVar("MinorVersionEnumType", bound=Enum)


def is_testing_context() -> bool:
    """
    Note that we check for the presence of the CLI environment
    variable and not the test case contextvars because the
    contextvars aren't set until run_test_suite is called,
    whereas a prompt manager might have already been imported
    and initialized by the time run_test_suite is called.
    """
    return bool(AutoblocksEnvVar.CLI_SERVER_ADDRESS.get())


def prompt_snapshots_map() -> dict[str, str]:
    """
    The AUTOBLOCKS_PROMPT_SNAPSHOTS environment variable is a JSON-stringified
    map of prompt IDs to snapshot IDs. This is set in CI test runs triggered
    from the UI.
    """
    if not is_testing_context():
        return {}

    prompt_snapshots_raw = AutoblocksEnvVar.PROMPT_SNAPSHOTS.get()
    if not prompt_snapshots_raw:
        return {}
    return json.loads(prompt_snapshots_raw)  # type: ignore


class AutoblocksPromptManager(
    abc.ABC,
    Generic[
        ExecutionContextType,
        MinorVersionEnumType,
    ],
):
    __prompt_id__: str
    __prompt_major_version__: str
    __execution_context_class__: Type[ExecutionContextType]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for attr in (
            "__prompt_id__",
            "__prompt_major_version__",
            "__execution_context_class__",
        ):
            if not hasattr(cls, attr):
                raise ValueError(f"AutoblocksPromptManager subclass {cls} must define {attr}")

    def __init__(
        self,
        minor_version: Union[
            MinorVersionEnumType,
            List[WeightedMinorVersion[MinorVersionEnumType]],
        ],
        api_key: Optional[str] = None,
        init_timeout: timedelta = timedelta(seconds=30),
        refresh_timeout: timedelta = timedelta(seconds=30),
        refresh_interval: timedelta = timedelta(seconds=10),
    ):
        global_state.init()
        self._class_name = type(self).__name__
        self._minor_version = PromptMinorVersion.model_validate({"version": minor_version})
        self._init_timeout = init_timeout
        self._refresh_timeout = refresh_timeout
        self._refresh_interval = refresh_interval
        self._minor_version_to_prompt: Dict[str, Prompt] = {}

        api_key = api_key or AutoblocksEnvVar.API_KEY.get()
        if not api_key:
            raise ValueError(
                f"You must either pass in the API key via 'api_key' or "
                f"set the {AutoblocksEnvVar.API_KEY} environment variable."
            )

        self._api_key = api_key

        self._prompt_snapshot: Optional[Prompt] = None

        refresh_seconds = refresh_interval.total_seconds()
        if refresh_seconds < 1:
            raise ValueError(f"Refresh interval can't be shorter than 1 second (got {refresh_seconds}s)")

        self._init()

        if LATEST in self._minor_version.all_minor_versions:
            if is_testing_context():
                log.info("Prompt refreshing is disabled when in a testing context.")
                return

            log.info(f"Refreshing latest prompt every {refresh_seconds} seconds")
            if running_loop := get_running_loop():
                running_loop.create_task(self._refresh_loop())
            else:
                asyncio.run_coroutine_threadsafe(
                    self._refresh_loop(),
                    global_state.event_loop(),
                )

    def _make_request_url(self, minor_version: str) -> str:
        prompt_id = encode_uri_component(self.__prompt_id__)
        major_version = encode_uri_component(self.__prompt_major_version__)
        minor_version = encode_uri_component(minor_version)
        return f"{API_ENDPOINT}/prompts/{prompt_id}/major/{major_version}/minor/{minor_version}"

    def _make_snapshot_validate_override_request_url(self, snapshot_id: str) -> str:
        prompt_id = encode_uri_component(self.__prompt_id__)
        snapshot_id = encode_uri_component(snapshot_id)
        return f"{API_ENDPOINT}/prompts/{prompt_id}/snapshots/{snapshot_id}/validate"

    async def _get_prompt(
        self,
        minor_version: str,
        timeout: timedelta,
    ) -> Prompt:
        resp = await global_state.http_client().get(
            self._make_request_url(minor_version),
            timeout=timeout.total_seconds(),
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        resp.raise_for_status()
        return Prompt.model_validate(resp.json())

    async def _set_prompt_snapshot(self, snapshot_id: str) -> None:
        """
        If this prompt has a snapshot set, use the /validate endpoint to check if the
        major version this prompt manager is configured to use is compatible to be
        overridden with the snapshot.
        """
        # Double check we're in a testing context
        if not is_testing_context():
            log.error("Can't set prompt snapshot unless in a testing context.")
            return

        # Double check the given snapshot_id belongs to this prompt manager
        expected_snapshot_id = prompt_snapshots_map()[self.__prompt_id__]
        if snapshot_id != expected_snapshot_id:
            raise RuntimeError(
                f"Snapshot ID '{snapshot_id}' does not match the snapshot ID "
                f"for this prompt manager '{expected_snapshot_id}'."
            )

        if self.__prompt_major_version__ == UNDEPLOYED:
            raise NotImplementedError(
                "Prompt snapshot overrides are not yet supported for prompt managers using DANGEROUSLY_USE_UNDEPLOYED. "
                "Reach out to support@autoblocks.ai for more details."
            )

        resp = await global_state.http_client().post(
            self._make_snapshot_validate_override_request_url(snapshot_id),
            timeout=self._init_timeout.total_seconds(),
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=dict(
                majorVersion=int(self.__prompt_major_version__),
            ),
        )

        if resp.status_code == HTTPStatus.CONFLICT:
            # The /validate endpoint returns this status code when the snapshot is
            # not compatible with the major version this prompt manager
            # is configured to use.
            raise IncompatiblePromptSnapshotError(
                f"Can't override '{self._class_name}' with prompt snapshot '{snapshot_id}' because it is not "
                f"compatible with major version '{self.__prompt_major_version__}'."
            )

        # Raise for any unexpected errors
        resp.raise_for_status()

        # Set the prompt snapshot
        log.warning(f"Overriding '{self._class_name}' with prompt snapshot '{snapshot_id}'!")
        self._prompt_snapshot = Prompt.model_validate(resp.json())

    async def _init_async(self) -> None:
        # Set the snapshot prompt if this manager's prompt ID is in the snapshot map
        if is_testing_context() and (snapshot_id := prompt_snapshots_map().get(self.__prompt_id__)):
            await self._set_prompt_snapshot(snapshot_id)
            return

        # Not in testing context or no snapshot set, proceed as configured

        # Convert all_minor_versions (which is a set) to a list
        # to guarantee we get the same order both when fetching
        # via gather and zipping together the minor versions to
        # their results.
        minor_versions = sorted(self._minor_version.all_minor_versions)
        try:
            prompts = await asyncio.gather(
                *[self._get_prompt(minor_version, self._init_timeout) for minor_version in minor_versions],
            )
        except Exception as err:
            log.error(f"Failed to initialize prompt manager for prompt '{self.__prompt_id__}': {err}")
            raise err

        for minor_version, prompt in zip(minor_versions, prompts):
            # Note that the key here is the minor version from the zipped
            # tuple, not `prompt.minor_version`. This is because the
            # latter will contain the actual version number, which may be
            # different from the minor version we requested (in the case
            # where we requested LATEST or UNDEPLOYED).
            self._minor_version_to_prompt[minor_version] = prompt
            log.info(f"Successfully fetched version '{prompt.version}' of prompt '{self.__prompt_id__}'")

    def _init(self) -> None:
        task: AnyTask
        if running_loop := get_running_loop():
            # If we're already in a running loop, execute the task on that loop
            task = running_loop.create_task(
                self._init_async(),
            )
        else:
            # Otherwise, send the task to our background loop
            task = asyncio.run_coroutine_threadsafe(
                self._init_async(),
                global_state.event_loop(),
            )

        # Wait for prompts to be initialized
        task.result()

        log.info("Successfully initialized prompt manager!")

    async def _refresh_loop(self) -> None:
        """
        Refreshes the latest version of the prompt every `refresh_interval` seconds.

        This isn't exactly "every n seconds" but more "run and then wait n seconds",
        which will cause it to drift each run by the time it takes to run the refresh,
        but I think that is ok in this scenario.
        """
        while True:
            await asyncio.sleep(self._refresh_interval.total_seconds())

            try:
                await self._refresh_latest()
            except Exception as err:
                log.warning(f"Failed to refresh latest prompt: {err}")

    async def _refresh_latest(self) -> None:
        # Get the latest minor version within this prompt's major version
        new_latest = await self._get_prompt(
            minor_version=LATEST,
            timeout=self._refresh_timeout,
        )

        # Get the prompt we're replacing
        old_latest = self._minor_version_to_prompt.get(LATEST)

        # Update the prompt
        self._minor_version_to_prompt[LATEST] = new_latest

        # Log if we're replacing an older version of the prompt
        if old_latest and old_latest.version != new_latest.version:
            log.info(f"Updated latest prompt from v{old_latest.version} to v{new_latest.version}")

    def _choose_execution_prompt(self) -> Prompt:
        # Always use the prompt snapshot if it is set
        if is_testing_context() and self._prompt_snapshot:
            return self._prompt_snapshot

        # Choose the minor version to use
        chosen_minor_version = self._minor_version.choose_version()

        # Return that version from the cache
        if chosen_minor_version in self._minor_version_to_prompt:
            return self._minor_version_to_prompt[chosen_minor_version]

        # This shouldn't happen, but the chosen version is not in the cache
        # Use the most recent cached prompt
        cache_keys = list(self._minor_version_to_prompt.keys())
        if cache_keys:
            last_in_cache = self._minor_version_to_prompt[cache_keys[-1]]
            log.error(
                f"Failed to choose execution prompt: "
                f"v{self.__prompt_major_version__}.{chosen_minor_version} not found.\n"
                f"Available versions are: {self._minor_version_to_prompt.keys()}.\n"
                f"Falling back to latest cached prompt: v{last_in_cache.version}."
            )
            return last_in_cache

        raise RuntimeError("Failed to choose execution prompt. No prompts available in cache.")

    def exec(self) -> ContextManager[ExecutionContextType]:
        """
        See https://youtrack.jetbrains.com/issue/PY-36444/PyCharm-doesnt-infer-types-when-using-contextlib.contextmanager-decorator
        for why this wraps a context manager instead of being a context manager itself.
        """

        @contextlib.contextmanager
        def gen():  # type: ignore
            prompt = self._choose_execution_prompt()
            yield self.__execution_context_class__(prompt=prompt)

        return gen()
