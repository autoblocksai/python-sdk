import logging
import os
import shutil

log = logging.getLogger(__name__)


class FileUtils:
    """Utility class for file operations related to code generation."""

    @staticmethod
    def ensure_directory_exists(directory_path: str) -> None:
        """Ensure a directory exists, creating it if necessary."""
        os.makedirs(directory_path, exist_ok=True)

    @staticmethod
    def clean_output_directory(output_dir: str) -> None:
        """Clean up an existing output directory to prepare for generation."""
        if not os.path.exists(output_dir):
            return

        log.info(f"Cleaning up existing directory: {output_dir}")

        # Log which files we're about to delete
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                path = os.path.join(root, file)
                log.debug(f"Removing file: {path}")

        # Only remove files in the apps directory and the __init__.py file
        apps_dir = os.path.join(output_dir, "apps")
        if os.path.exists(apps_dir):
            shutil.rmtree(apps_dir)

        init_file = os.path.join(output_dir, "__init__.py")
        if os.path.exists(init_file):
            os.remove(init_file)

    @staticmethod
    def write_to_file(file_path: str, content: str) -> None:
        """Write content to a file, creating parent directories if needed."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
