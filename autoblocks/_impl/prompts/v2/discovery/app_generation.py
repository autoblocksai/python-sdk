from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from autoblocks._impl.prompts.utils import normalize_app_name
from autoblocks._impl.prompts.utils import to_snake_case
from autoblocks._impl.prompts.utils import to_title_case
from autoblocks._impl.prompts.v2.client import PromptsAPIClient
from autoblocks._impl.prompts.v2.discovery.file_utils import FileUtils
from autoblocks._impl.prompts.v2.discovery.prompts import generate_prompt_implementations
from autoblocks._impl.prompts.v2.models import Prompt


class AppGenerator:
    """Generates code for specific apps and their prompts."""

    def __init__(self, output_dir: str, file_utils: Optional[FileUtils] = None):
        self.output_dir = output_dir
        self.file_utils = file_utils or FileUtils()

    def generate_app_init(self, app_name: str, app_id: str, prompts: List[Prompt]) -> None:
        """Generate the __init__.py file for an app."""
        normalized_name = normalize_app_name(app_name)
        app_dir = f"{self.output_dir}/apps/{normalized_name}"
        self.file_utils.ensure_directory_exists(app_dir)

        init_code = [
            "# Auto-generated prompt module for app: " + app_name,
            "from typing import Optional",
            "from typing import Union",
            "",
            "from . import prompts",
            "",
        ]

        # Export prompt factory functions
        for prompt in prompts:
            prompt_id = prompt.id
            title_case_id = to_title_case(prompt_id)
            snake_case = to_snake_case(prompt_id)
            function_name = f"{snake_case}_prompt_manager"

            # Determine the return type based on versions
            if prompt.is_undeployed:
                return_type = f"prompts._{title_case_id}UndeployedPromptManager"
            else:
                major_version_strings = [mv.major_version for mv in prompt.major_versions]
                if len(major_version_strings) == 1:
                    return_type = f"prompts._{title_case_id}V{major_version_strings[0]}PromptManager"
                else:
                    version_managers = [
                        f"prompts._{title_case_id}V{v}PromptManager" for v in sorted(major_version_strings)
                    ]
                    return_type = f"Union[{', '.join(version_managers)}]"

            # Function parameters with defaults
            init_code.extend(
                [
                    f"def {function_name}(",
                    "    major_version: "
                    + ('str = "undeployed"' if prompt.is_undeployed else "Optional[str] = None")
                    + ",",
                    "    minor_version: str = '0',",
                    "    api_key: Optional[str] = None,",
                    "    init_timeout: Optional[float] = None,",
                    "    refresh_timeout: Optional[float] = None,",
                    "    refresh_interval: Optional[float] = None,",
                    f") -> {return_type}:",
                    f"    return prompts.{title_case_id}Factory.create(",
                    "        major_version=major_version,",
                    "        minor_version=minor_version,",
                    "        api_key=api_key,",
                    "        init_timeout=init_timeout,",
                    "        refresh_timeout=refresh_timeout,",
                    "        refresh_interval=refresh_interval,",
                    "    )",
                    "",
                ]
            )

        # Write to file
        self.file_utils.write_to_file(f"{app_dir}/__init__.py", "\n".join(init_code))

    def generate_app_prompts(
        self, app_name: str, app_id: str, prompts: List[Prompt], api_client: Optional[PromptsAPIClient] = None
    ) -> None:
        """Generate the prompts.py file for an app."""
        normalized_name = normalize_app_name(app_name)
        app_dir = f"{self.output_dir}/apps/{normalized_name}"
        self.file_utils.ensure_directory_exists(app_dir)

        # Add imports at the beginning of the file
        imports = [
            "from typing import Any",
            "from typing import Dict",
            "from typing import List",
            "from typing import Optional",
            "from typing import Union",
            "",
            "import pydantic",
            "",
            "from autoblocks.prompts.v2.models import FrozenModel",
            "from autoblocks.prompts.v2.context import PromptExecutionContext",
            "from autoblocks.prompts.v2.manager import AutoblocksPromptManager",
            "from autoblocks.prompts.v2.renderer import TemplateRenderer, ToolRenderer",
            "",
            "",
        ]

        # Generate implementations for each prompt, removing any existing imports
        prompt_impls = []
        for prompt in prompts:
            implementation = generate_prompt_implementations(app_id, app_name, prompt, api_client)
            prompt_impls.append(implementation)

        # Write to file with two empty lines between classes
        self.file_utils.write_to_file(f"{app_dir}/prompts.py", "\n".join(imports) + "\n" + "\n\n".join(prompt_impls))

    def create_root_init(self, apps: List[Dict[str, Any]]) -> None:
        """Create the root __init__.py file."""
        # Create apps package __init__.py
        apps_dir = f"{self.output_dir}/apps"
        self.file_utils.ensure_directory_exists(apps_dir)

        self.file_utils.write_to_file(f"{apps_dir}/__init__.py", "# Auto-generated app package\n")

        # Create root __init__.py with imports
        init_lines = [
            "# Auto-generated prompt modules",
            "# DO NOT EDIT THIS FILE MANUALLY",
            "",
            "# Import all app modules",
        ]

        # Add import statements for apps
        app_names = [normalize_app_name(app["app_name"]) for app in apps]
        init_lines.extend([f"from .apps import {name}" for name in app_names])

        # Add module-level variables
        init_lines.append("\n# Make apps available at top level")
        init_lines.extend([f"{name} = {name}" for name in app_names])

        # Write to file
        self.file_utils.write_to_file(f"{self.output_dir}/__init__.py", "\n".join(init_lines))
