import abc
import asyncio
import contextlib
import json
import logging
from datetime import timedelta
from http import HTTPStatus
from typing import Any, ContextManager, Dict, Generic, List, Optional, Type, TypeVar, Union

from autoblocks._impl import global_state
from autoblocks._impl.api.v2.client import AutoblocksAPIClient
from autoblocks._impl.api.v2.models import Prompt, PromptMajorVersion
from autoblocks._impl.config.constants import V2_API_ENDPOINT
from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.prompts.models import PromptMinorVersion, WeightedMinorVersion
from autoblocks._impl.prompts.v2.context import PromptExecutionContext
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import encode_uri_component
from autoblocks._impl.util import get_running_loop

log = logging.getLogger(__name__)

ExecutionContextType = TypeVar("ExecutionContextType", bound=PromptExecutionContext[Any, Any, Any])


def is_testing_context() -> bool:
    """Check if the current context is a testing context."""
    return bool(AutoblocksEnvVar.CLI_SERVER_ADDRESS.get())


class AutoblocksPromptManager(
    abc.ABC,
    Generic[ExecutionContextType],
):
    """Base class for V2 prompt managers.
    
    Each prompt manager corresponds to a specific prompt in the Autoblocks platform.
    """
    __prompt_id__: str
    __app_id__: str  # New field for V2
    __prompt_major_version__: str
    __execution_context_class__: Type[ExecutionContextType]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for attr in (
            "__prompt_id__",
            "__app_id__",  # Require app_id for V2
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
        """Initialize a prompt manager.
        
        Args:
            minor_version: The minor version to use, or a list of weighted minor versions.
            api_key: The API key to use. If None, will try to read from environment.
            init_timeout: Timeout for the initial prompt fetch.
            refresh_timeout: Timeout for refreshing prompts.
            refresh_interval: Interval between refreshes.
        """
        global_state.init()
        self._class_name = type(self).__name__
        self._minor_version = PromptMinorVersion.model_validate({"version": minor_version})
        self._init_timeout = init_timeout
        self._refresh_timeout = refresh_timeout
        self._refresh_interval = refresh_interval
        self._minor_version_to_prompt: Dict[str, Prompt] = {}
        self._major_versions: Dict[str, PromptMajorVersion] = {}

        api_key = api_key or AutoblocksEnvVar.V2_API_KEY.get()
        if not api_key:
            raise ValueError(
                f"You must either pass in the API key via 'api_key' or "
                f"set the {AutoblocksEnvVar.V2_API_KEY} environment variable."
            )

        self._api_key = api_key
        self._client = AutoblocksAPIClient(api_key=api_key)
        self._init()
        
        # Setup refresh logic for LATEST minor version if needed
        if REVISION_LATEST in self._minor_version.all_minor_versions:
            if is_testing_context():
                log.info("Prompt refreshing is disabled when in a testing context.")
                return

            refresh_seconds = refresh_interval.total_seconds()
            log.info(f"Refreshing latest prompt every {refresh_seconds} seconds")
            if running_loop := get_running_loop():
                running_loop.create_task(self._refresh_loop())
            else:
                asyncio.run_coroutine_threadsafe(
                    self._refresh_loop(),
                    global_state.event_loop(),
                )
        
    def _init(self):
        """Initialize the prompt manager by fetching prompts."""
        for minor_version in self._minor_version.all_minor_versions:
            self._fetch_prompt(minor_version)
    
    def _fetch_prompt(self, minor_version: str):
        """Fetch a prompt for a specific minor version."""
        prompt = self._client.get_prompt(
            app_id=self.__app_id__,
            prompt_id=self.__prompt_id__,
            major_version=self.__prompt_major_version__,
            minor_version=minor_version,
            timeout=self._init_timeout
        )
        
        major_version = None
        for mv in prompt.major_versions:
            if mv.major_version == self.__prompt_major_version__:
                major_version = mv
                break
                
        if not major_version:
            raise ValueError(f"Major version {self.__prompt_major_version__} not found in prompt {prompt.id}")
        
        self._minor_version_to_prompt[minor_version] = prompt
        self._major_versions[minor_version] = major_version
            
    async def _refresh_loop(self):
        """Periodically refresh the prompt."""
        while True:
            try:
                await asyncio.sleep(self._refresh_interval.total_seconds())
                for minor_version in self._minor_version.all_minor_versions:
                    if minor_version == REVISION_LATEST:
                        self._fetch_prompt(minor_version)
            except Exception as e:
                log.error(f"Error refreshing prompt: {e}")
                
    @contextlib.contextmanager
    def exec(self) -> ContextManager[ExecutionContextType]:
        """Get an execution context for this prompt.
        
        Returns:
            A context manager that yields an execution context.
        """
        minor_version = self._minor_version.choose_version()
        
        # Ensure we have fetched this minor version
        if minor_version not in self._minor_version_to_prompt:
            self._fetch_prompt(minor_version)
            
        prompt = self._minor_version_to_prompt[minor_version]
        major_version = self._major_versions[minor_version]
        
        # Create and yield execution context
        context = self.__execution_context_class__(prompt, major_version)
        try:
            yield context
        finally:
            pass 