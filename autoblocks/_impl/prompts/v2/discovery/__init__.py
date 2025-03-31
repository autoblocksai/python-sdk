import logging
from typing import Dict
from typing import List
from typing import Optional
from typing import cast

from autoblocks._impl.prompts.v2.client import PromptsAPIClient
from autoblocks._impl.prompts.v2.discovery.app_generation import AppGenerator
from autoblocks._impl.prompts.v2.discovery.file_utils import FileUtils
from autoblocks._impl.prompts.v2.discovery.models import AppData
from autoblocks._impl.prompts.v2.models import Prompt

log = logging.getLogger(__name__)


class PromptModulesGenerator:
    """Main class responsible for generating all prompt modules."""

    def __init__(self, api_key: Optional[str], output_dir: str):
        """Initialize the generator.

        Args:
            api_key: Optional API key for Autoblocks API.
            output_dir: Directory where generated code will be written.
        """
        self.api_key = api_key
        self.output_dir = output_dir
        self.client = PromptsAPIClient(api_key=api_key)
        self.file_utils = FileUtils()
        self.app_generator = AppGenerator(output_dir, self.file_utils)

    def generate(self) -> None:
        """Generate all prompt modules."""
        # Clean up existing directory
        self.file_utils.clean_output_directory(self.output_dir)

        # Fetch all prompts
        all_prompts = self.client.get_all_prompts()

        # Group prompts by app
        apps_map = self._group_prompts_by_app(all_prompts)

        # Create base directories
        self._prepare_directories(apps_map)

        # Generate code for each app
        self._generate_app_code(apps_map)

        log.info(f"Generated modules for {len(apps_map)} apps with {len(all_prompts)} prompts")

    def _group_prompts_by_app(self, prompts: List[Prompt]) -> Dict[str, AppData]:
        """Group prompts by their app ID.

        Args:
            prompts: List of prompts to group.

        Returns:
            Dictionary mapping app IDs to app data.
        """
        apps_map: Dict[str, AppData] = {}

        for prompt in prompts:
            app_id = prompt.app_id

            if app_id not in apps_map:
                apps_map[app_id] = {"app_id": app_id, "app_name": prompt.app_name, "prompts": []}

            prompts_list = cast(List[Prompt], apps_map[app_id]["prompts"])
            prompts_list.append(prompt)
        return apps_map

    def _prepare_directories(self, apps_map: Dict[str, AppData]) -> None:
        """Prepare the directory structure for code generation.

        Args:
            apps_map: Dictionary mapping app IDs to app data.
        """
        self.file_utils.ensure_directory_exists(self.output_dir)
        if apps_map:
            self.file_utils.ensure_directory_exists(f"{self.output_dir}/apps")

    def _generate_app_code(self, apps_map: Dict[str, AppData]) -> None:
        """Generate code for each app.

        Args:
            apps_map: Dictionary mapping app IDs to app data.
        """
        for app_id, app_data in apps_map.items():
            app_name = app_data["app_name"]
            prompts = cast(List[Prompt], app_data["prompts"])

            # Generate app files
            self.app_generator.generate_app_init(app_name, app_id, prompts)
            self.app_generator.generate_app_prompts(app_name, app_id, prompts, self.client)

        # Create root init
        self.app_generator.create_root_init(list(apps_map.values()))


def generate_all_prompt_modules(api_key: Optional[str] = None, output_dir: Optional[str] = None) -> None:
    """Generate all prompt modules from the API.

    Args:
        api_key: Optional API key for Autoblocks API
        output_dir: Directory where generated code will be written

    Raises:
        ValueError: If output_dir is not specified
    """
    if not output_dir:
        raise ValueError("Output directory must be specified")

    log.info(f"Generating V2 prompt modules in {output_dir}")

    generator = PromptModulesGenerator(api_key, output_dir)
    generator.generate()
