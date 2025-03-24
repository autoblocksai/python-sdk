import abc
import asyncio
import contextlib
import json
import logging
import random
from datetime import timedelta
from typing import Any, ContextManager, Dict, Generic, List, Optional, TypeVar, Union

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.prompts.v2.models import PromptMinorVersion, WeightedMinorVersion
from autoblocks._impl.util import AnyTask, AutoblocksEnvVar, encode_uri_component, get_running_loop
from autoblocks.prompts.v2.context import PromptExecutionContext

log = logging.getLogger(__name__)

ExecutionContextType = TypeVar("ExecutionContextType", bound=PromptExecutionContext[Any, Any, Any])


class AutoblocksPromptManager(
    abc.ABC,
    Generic[ExecutionContextType],
):
    """
    Manager for V2 prompts.
    This handles fetching, versioning, and execution of prompts.
    """
    __app_id__: str
    __prompt_id__: str
    __prompt_major_version__: str
    __execution_context_class__: type[ExecutionContextType]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for attr in (
            "__app_id__",
            "__prompt_id__",
            "__prompt_major_version__",
            "__execution_context_class__",
        ):
            if not hasattr(cls, attr):
                raise ValueError(f"AutoblocksPromptManager subclass {cls} must define {attr}")

    def __init__(
        self,
        minor_version: Union[
            str,
            List[WeightedMinorVersion],
        ],
        api_key: Optional[str] = None,
        init_timeout: timedelta = timedelta(seconds=30),
        refresh_timeout: timedelta = timedelta(seconds=30),
        refresh_interval: timedelta = timedelta(seconds=10),
    ):
        """
        Initialize the prompt manager.
        
        Args:
            minor_version: The minor version to use, or a list of weighted minor versions for A/B testing
            api_key: The API key to use. If None, the API key is read from the environment.
            init_timeout: Timeout for initialization
            refresh_timeout: Timeout for refreshing the prompt
            refresh_interval: Interval between refreshes for "latest" minor versions
        """
        global_state.init()
        self._class_name = type(self).__name__
        self._minor_version = PromptMinorVersion.model_validate({"version": minor_version})
        self._init_timeout = init_timeout
        self._refresh_timeout = refresh_timeout
        self._refresh_interval = refresh_interval
        self._minor_version_to_prompt: Dict[str, Dict[str, Any]] = {}

        api_key = api_key or AutoblocksEnvVar.V2_API_KEY.get()
        if not api_key:
            raise ValueError(
                f"You must either pass in the API key via 'api_key' or "
                f"set the {AutoblocksEnvVar.V2_API_KEY} environment variable."
            )

        self._api_key = api_key

        refresh_seconds = refresh_interval.total_seconds()
        if refresh_seconds < 1:
            raise ValueError(f"Refresh interval can't be shorter than 1 second (got {refresh_seconds}s)")

        self._init()

        if REVISION_LATEST in self._minor_version.all_minor_versions:
            log.info(f"Refreshing latest prompt every {refresh_seconds} seconds")
            if running_loop := get_running_loop():
                running_loop.create_task(self._refresh_loop())
            else:
                asyncio.run_coroutine_threadsafe(
                    self._refresh_loop(),
                    global_state.event_loop(),
                )

    def _make_request_url(self, minor_version: str) -> str:
        """
        Make the URL for a request to the API.
        
        Args:
            minor_version: The minor version
            
        Returns:
            The URL for the request
        """
        app_id = encode_uri_component(self.__app_id__)
        prompt_id = encode_uri_component(self.__prompt_id__)
        major_version = encode_uri_component(self.__prompt_major_version__)
        minor_version = encode_uri_component(minor_version)
        
        return f"/v2/apps/{app_id}/prompts/{prompt_id}/major/{major_version}/minor/{minor_version}"

    async def _get_prompt(
        self,
        minor_version: str,
        timeout: timedelta,
    ) -> Dict[str, Any]:
        """
        Get a prompt from the API.
        
        Args:
            minor_version: The minor version
            timeout: The timeout for the request
            
        Returns:
            The prompt data
        """
        resp = await global_state.http_client().get(
            self._make_request_url(minor_version),
            timeout=timeout.total_seconds(),
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def _init_async(self) -> None:
        """Initialize the prompt manager asynchronously."""
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
            # where we requested LATEST).
            self._minor_version_to_prompt[minor_version] = prompt
            log.info(f"Successfully fetched version '{prompt.get('version')}' of prompt '{self.__prompt_id__}'")

    def _init(self) -> None:
        """Initialize the prompt manager."""
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
        """Refresh the prompt periodically if using "latest" minor version."""
        while True:
            try:
                await asyncio.sleep(self._refresh_interval.total_seconds())
                await self._refresh_latest_minor_versions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Error refreshing prompts: {e}")

    async def _refresh_latest_minor_versions(self) -> None:
        """Refresh all prompts with "latest" minor version."""
        for minor_version in list(self._minor_version_to_prompt.keys()):
            if minor_version == REVISION_LATEST:
                try:
                    new_prompt = await self._get_prompt(minor_version, self._refresh_timeout)
                    if new_prompt.get("revisionId") != self._minor_version_to_prompt[minor_version].get("revisionId"):
                        log.info(f"Refreshed latest prompt for '{self.__prompt_id__}'")
                        self._minor_version_to_prompt[minor_version] = new_prompt
                except Exception as e:
                    log.error(f"Failed to refresh latest prompt for '{self.__prompt_id__}': {e}")

    @contextlib.contextmanager
    def exec(self) -> ContextManager[ExecutionContextType]:
        """
        Execute a prompt in a context manager.
        
        Returns:
            A context manager that yields an execution context
        """
        version = self._minor_version.choose_version()
        prompt = self._minor_version_to_prompt[version]
        context = self.__execution_context_class__(prompt)
        try:
            yield context
        finally:
            pass 