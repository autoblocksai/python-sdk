import abc
import concurrent.futures
import contextlib
import logging
import threading
import time
from datetime import timedelta
from enum import Enum
from typing import ContextManager
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Type
from typing import TypeVar
from typing import Union

import httpx

from autoblocks._impl.prompts.constants import LATEST
from autoblocks._impl.prompts.context import PromptExecutionContext
from autoblocks._impl.prompts.models import HeadlessPrompt
from autoblocks._impl.prompts.models import PromptMinorVersion
from autoblocks._impl.prompts.models import WeightedMinorVersion
from autoblocks._impl.util import AutoblocksEnvVar
from autoblocks._impl.util import encode_uri_component

log = logging.getLogger(__name__)

global_api_client = None


def get_or_create_api_client(api_key: str) -> httpx.Client:
    global global_api_client
    if global_api_client is None:
        global_api_client = httpx.Client(
            base_url="https://api.autoblocks.ai",
            headers={"Authorization": f"Bearer {api_key}"},
        )
    return global_api_client


ExecutionContextType = TypeVar("ExecutionContextType", bound=PromptExecutionContext)
MinorVersionEnumType = TypeVar("MinorVersionEnumType", bound=Enum)


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

    def __init_subclass__(cls, **kwargs):
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
        self._minor_version = PromptMinorVersion.model_validate({"version": minor_version})
        self._refresh_timeout = refresh_timeout
        self._refresh_interval = refresh_interval
        self._minor_version_to_prompt: Dict[str, HeadlessPrompt] = {}

        api_key = api_key or AutoblocksEnvVar.API_KEY.get()
        if not api_key:
            raise ValueError(
                f"You must either pass in the API key via 'api_key' or "
                f"set the {AutoblocksEnvVar.API_KEY} environment variable."
            )

        refresh_seconds = refresh_interval.total_seconds()
        if refresh_seconds < 1:
            raise ValueError(f"Refresh interval can't be shorter than 1 second (got {refresh_seconds}s)")

        self._client = get_or_create_api_client(api_key)

        self._init(init_timeout)

        if LATEST in self._minor_version.all_minor_versions:
            log.info(f"Refreshing latest prompt every {refresh_seconds} seconds")
            # Since this is a daemon thread, we don't need to expose a way to explicitly
            # stop it. It will be stopped when the main thread exits.
            self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
            self._refresh_thread.start()

    def _make_request_url(self, minor_version: str) -> str:
        prompt_id = encode_uri_component(self.__prompt_id__)
        major_version = encode_uri_component(self.__prompt_major_version__)
        minor_version = encode_uri_component(minor_version)
        return f"/prompts/{prompt_id}/major/{major_version}/minor/{minor_version}"

    def _get_prompt(
        self,
        minor_version: str,
        timeout: timedelta,
    ) -> HeadlessPrompt:
        resp = self._client.get(
            self._make_request_url(minor_version),
            timeout=timeout.total_seconds(),
        )
        resp.raise_for_status()
        return HeadlessPrompt.model_validate(resp.json())

    def _init(self, timeout: timedelta) -> None:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_minor_version: Dict[concurrent.futures.Future, str] = {
                executor.submit(
                    self._get_prompt,
                    minor_version,
                    timeout,
                ): minor_version
                for minor_version in self._minor_version.all_minor_versions
            }

            for future in concurrent.futures.as_completed(future_to_minor_version):
                minor_version = future_to_minor_version[future]
                try:
                    prompt = future.result()
                    # Note that the key here is the minor version from the futures
                    # dictionary, not `prompt.minor_version`. This is because the
                    # latter will contain the actual version number, which may be
                    # different from the minor version we requested (in the case
                    # where we requested LATEST).
                    self._minor_version_to_prompt[minor_version] = prompt
                    log.info(f"Successfully fetched version v{self.__prompt_major_version__}.{prompt.minor_version}")
                except Exception as err:
                    log.error(f"Failed to fetch version v{self.__prompt_major_version__}.{minor_version}: {err}")
                    raise err

        log.info("Successfully initialized prompt manager!")

    def _refresh_loop(self) -> None:
        """
        Runs in a background thread and refreshes the latest version of the prompt
        every `refresh_interval` seconds.

        This isn't exactly "every n seconds" but more "run and then wait n seconds",
        which will cause it to drift each run by the time it takes to run the refresh,
        but I think that is ok in this scenario.
        """
        while True:
            time.sleep(self._refresh_interval.total_seconds())

            try:
                self._refresh_latest()
            except Exception as err:
                log.warning(f"Failed to refresh latest prompt: {err}")

    def _refresh_latest(self):
        # Get the latest minor version within this prompt's major version
        new_latest = self._get_prompt(
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

    def _choose_execution_prompt(self) -> HeadlessPrompt:
        rand_version = self._minor_version.random_version()
        if rand_version in self._minor_version_to_prompt:
            return self._minor_version_to_prompt[rand_version]

        cache_keys = list(self._minor_version_to_prompt.keys())
        if cache_keys:
            last_in_cache = self._minor_version_to_prompt[cache_keys[-1]]
            log.error(
                f"Failed to choose execution prompt: v{self.__prompt_major_version__}.{rand_version} not found.\n"
                f"Available versions are: {self._minor_version_to_prompt.keys()}.\n"
                f"Using cached prompt: v{last_in_cache.version}."
            )
            return last_in_cache

        raise RuntimeError("Failed to choose execution prompt. No prompts available in cache.")

    def exec(self) -> ContextManager[ExecutionContextType]:
        """
        See https://youtrack.jetbrains.com/issue/PY-36444/PyCharm-doesnt-infer-types-when-using-contextlib.contextmanager-decorator
        for why this wraps a context manager instead of being a context manager itself.
        """

        @contextlib.contextmanager
        def gen():
            prompt = self._choose_execution_prompt()
            yield self.__execution_context_class__(prompt=prompt)

        return gen()
