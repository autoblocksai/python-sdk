import abc
import asyncio
import contextlib
import logging
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Generic
from typing import Iterator
from typing import Optional
from typing import TypeVar

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.prompts.v2.client import PromptsAPIClient
from autoblocks._impl.prompts.v2.context import PromptExecutionContext
from autoblocks._impl.prompts.v2.models import PromptMinorVersion
from autoblocks._impl.util import AnyTask
from autoblocks._impl.util import get_running_loop

log = logging.getLogger(__name__)

ParamsType = TypeVar("ParamsType")
TemplateRendererType = TypeVar("TemplateRendererType")
ToolRendererType = TypeVar("ToolRendererType")

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
        minor_version: str,
        api_key: Optional[str] = None,
        init_timeout: timedelta = timedelta(seconds=30),
        refresh_timeout: timedelta = timedelta(seconds=30),
        refresh_interval: timedelta = timedelta(seconds=10),
    ):
        """
        Initialize the prompt manager.

        Args:
            minor_version: The minor version to use
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

        # Initialize API client
        self._client = PromptsAPIClient(api_key=api_key)

        # Validate refresh interval
        refresh_seconds = refresh_interval.total_seconds()
        if refresh_seconds < 1:
            raise ValueError(f"Refresh interval can't be shorter than 1 second (got {refresh_seconds}s)")

        # Initialize prompts
        self._init()

        # Set up periodic refresh for latest versions
        if self._minor_version.version == REVISION_LATEST or self.__prompt_major_version__ == REVISION_UNDEPLOYED:
            log.info(f"Refreshing latest prompt every {refresh_seconds} seconds")
            if running_loop := get_running_loop():
                running_loop.create_task(self._refresh_loop())
            else:
                asyncio.run_coroutine_threadsafe(
                    self._refresh_loop(),
                    global_state.event_loop(),
                )

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
        return await self._client.get_prompt_async(
            app_id=self.__app_id__,
            prompt_id=self.__prompt_id__,
            major_version=self.__prompt_major_version__,
            minor_version=minor_version,
            timeout=timeout,
        )

    async def _init_async(self) -> None:
        """Initialize the prompt manager asynchronously."""
        # No longer need to extract from all_minor_versions since we only have a single version
        try:
            prompt = await self._get_prompt(self._minor_version.version, self._init_timeout)
        except Exception as err:
            log.error(f"Failed to initialize prompt manager for prompt '{self.__prompt_id__}': {err}")
            raise err

        # Store the prompt data
        self._minor_version_to_prompt[self._minor_version.version] = prompt
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
        minor_version = self._minor_version.version
        # Refresh prompts with "latest" minor version or if this is an undeployed prompt
        if minor_version == REVISION_LATEST or self.__prompt_major_version__ == REVISION_UNDEPLOYED:
            try:
                new_prompt = await self._get_prompt(minor_version, self._refresh_timeout)
                if new_prompt.get("revisionId") != self._minor_version_to_prompt[minor_version].get("revisionId"):
                    log.info(f"Refreshed latest prompt for '{self.__prompt_id__}'")
                    self._minor_version_to_prompt[minor_version] = new_prompt
            except Exception as e:
                log.error(f"Failed to refresh latest prompt for '{self.__prompt_id__}': {e}")

    @contextlib.contextmanager
    def exec(self) -> Iterator[ExecutionContextType]:
        """
        Execute a prompt in a context manager.

        Returns:
            A context manager that yields an execution context
        """
        version = self._minor_version.version
        prompt = self._minor_version_to_prompt[version]
        context = self.__execution_context_class__(prompt)
        try:
            yield context
        finally:
            pass
