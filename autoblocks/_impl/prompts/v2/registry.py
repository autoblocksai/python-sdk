from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import TypeVar

T = TypeVar("T")


class PromptRegistry:
    """Registry of all prompt managers available in the platform."""

    _registry: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register_app(cls, app_id: str, app_name: str, normalized_name: str) -> Dict[str, Any]:
        """
        Register an app in the registry.

        Args:
            app_id: The app ID
            app_name: The original app name
            normalized_name: The normalized app name (valid Python identifier)

        Returns:
            The app entry in the registry
        """
        if normalized_name not in cls._registry:
            cls._registry[normalized_name] = {"app_id": app_id, "app_name": app_name, "prompts": {}}
        return cls._registry[normalized_name]

    @classmethod
    def register_prompt(
        cls, app_normalized_name: str, prompt_id: str, factory_func: Callable[..., T], major_versions: List[str]
    ) -> None:
        """
        Register a prompt in an app.

        Args:
            app_normalized_name: The normalized app name
            prompt_id: The prompt ID
            factory_func: The factory function to create prompt managers
            major_versions: Available major versions
        """
        app = cls._registry.get(app_normalized_name)
        if app:
            app["prompts"][prompt_id] = {"factory": factory_func, "major_versions": major_versions}

    @classmethod
    def get_all_apps(cls) -> Dict[str, Dict[str, Any]]:
        """Get all registered apps."""
        return cls._registry
