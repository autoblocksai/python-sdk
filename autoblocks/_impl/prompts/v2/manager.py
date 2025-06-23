import abc
import asyncio
import contextlib
import json
import logging
from datetime import timedelta
from http import HTTPStatus
from typing import Any
from typing import Dict
from typing import Generic
from typing import Iterator
from typing import Optional
from typing import TypeVar

from autoblocks._impl import global_state
from autoblocks._impl.config.constants import API_ENDPOINT_V2
from autoblocks._impl.config.constants import REVISION_LATEST
from autoblocks._impl.config.constants import REVISION_UNDEPLOYED
from autoblocks._impl.context_vars import RevisionType
from autoblocks._impl.context_vars import register_revision_usage
from autoblocks._impl.prompts.error import IncompatiblePromptRevisionError
from autoblocks._impl.prompts.v2.client import PromptsAPIClient
from autoblocks._impl.prompts.v2.context import PromptExecutionContext
from autoblocks._impl.prompts.v2.models import PromptMinorVersion
from autoblocks._impl.util import AnyTask
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import encode_uri_component
from autoblocks._impl.util import get_running_loop
from autoblocks._impl.util import parse_autoblocks_overrides

log = logging.getLogger(__name__)

ParamsType = TypeVar("ParamsType")
TemplateRendererType = TypeVar("TemplateRendererType")
ToolRendererType = TypeVar("ToolRendererType")

ExecutionContextType = TypeVar("ExecutionContextType", bound=PromptExecutionContext[Any, Any, Any])


def is_testing_context() -> bool:
    """
    Note that we check for the presence of V2_CI_TEST_RUN_BUILD_ID
    """
    return bool(AutoblocksEnvVar.V2_CI_TEST_RUN_BUILD_ID.get())


def prompt_revisions_map() -> dict[str, str]:
    """
    The AUTOBLOCKS_OVERRIDES environment variable is a JSON-stringified
    object that can contain promptRevisions. This is set in CI test runs triggered
    from the UI. Falls back to legacy AUTOBLOCKS_OVERRIDES_PROMPT_REVISIONS.
    """
    if not is_testing_context():
        return {}

    # Try new unified format first
    overrides = parse_autoblocks_overrides()
    if overrides.prompt_revisions:
        return overrides.prompt_revisions

    # Fallback to legacy format
    prompt_revisions_raw = AutoblocksEnvVar.OVERRIDES_PROMPT_REVISIONS.get()
    if not prompt_revisions_raw:
        return {}
    return json.loads(prompt_revisions_raw)  # type: ignore


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

        self._prompt_revision_override: Optional[Dict[str, Any]] = None

        # Validate refresh interval
        refresh_seconds = refresh_interval.total_seconds()
        if refresh_seconds < 1:
            raise ValueError(f"Refresh interval can't be shorter than 1 second (got {refresh_seconds}s)")

        # Initialize prompts
        self._init()

        # Set up periodic refresh for latest versions
        if self._minor_version.version == REVISION_LATEST or self.__prompt_major_version__ == REVISION_UNDEPLOYED:
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
        # Check for revision override first
        if is_testing_context() and (revision_id := prompt_revisions_map().get(self.__prompt_id__)):
            await self._set_prompt_revision(revision_id)
            return

        # Normal initialization logic
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
        # Choose prompt with override priority
        if is_testing_context() and self._prompt_revision_override:
            prompt = self._prompt_revision_override
        else:
            version = self._minor_version.version
            prompt = self._minor_version_to_prompt[version]

        # Register revision usage for tracking
        if is_testing_context():
            entity_id = prompt.get("id")
            revision_id = prompt.get("revisionId")
            if entity_id and revision_id:
                register_revision_usage(
                    entity_id=entity_id,
                    entity_type=RevisionType.PROMPT,
                    revision_id=revision_id,
                )

        context = self.__execution_context_class__(prompt)
        try:
            yield context
        finally:
            pass

    def _make_revision_validate_override_request_url(self, revision_id: str) -> str:
        """
        Construct the V2 validation endpoint URL.
        V2 pattern: /apps/:appId/prompts/:externalId/revisions/:revisionId/validate
        """
        app_id = encode_uri_component(self.__app_id__)
        prompt_id = encode_uri_component(self.__prompt_id__)
        revision_id = encode_uri_component(revision_id)
        return f"{API_ENDPOINT_V2}/apps/{app_id}/prompts/{prompt_id}/revisions/{revision_id}/validate"

    async def _set_prompt_revision(self, revision_id: str) -> None:
        """
        If this prompt has a revision override set, use the /validate endpoint to
        check if the major version this prompt manager is configured to use is compatible
        to be overridden with the revision.
        """
        # Double check we're in a testing context
        if not is_testing_context():
            log.error("Can't set prompt revision unless in a testing context.")
            return

        # Double check the given revision_id belongs to this prompt manager
        expected_revision_id = prompt_revisions_map()[self.__prompt_id__]
        if revision_id != expected_revision_id:
            raise RuntimeError(
                f"Revision ID '{revision_id}' does not match the revision ID "
                f"for this prompt manager '{expected_revision_id}'."
            )

        resp = await global_state.http_client().post(
            self._make_revision_validate_override_request_url(revision_id),
            timeout=self._init_timeout.total_seconds(),
            headers={"Authorization": f"Bearer {self._client._api_key}"},
            json=dict(
                majorVersion=int(self.__prompt_major_version__),
            ),
        )

        if resp.status_code == HTTPStatus.CONFLICT:
            # The /validate endpoint returns this status code when the revision is
            # not compatible with the major version this prompt manager
            # is configured to use.
            raise IncompatiblePromptRevisionError(
                f"Can't override prompt '{self._class_name}' with revision '{revision_id}' because it is not "
                f"compatible with major version '{self.__prompt_major_version__}'."
            )

        # Raise for any unexpected errors
        resp.raise_for_status()

        # Set the prompt revision override
        log.warning(f"Overriding prompt '{self._class_name}' with revision '{revision_id}'!")
        response_data = resp.json()
        # Ensure appId is included in the response data
        response_data["appId"] = self.__app_id__
        self._prompt_revision_override = response_data
