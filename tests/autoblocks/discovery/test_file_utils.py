import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from autoblocks._impl.prompts.v2.discovery.file_utils import FileUtils


class TestFileUtils:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Clean up
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    def test_ensure_directory_exists_new(self, temp_dir):
        # Test creating a new directory
        test_dir = os.path.join(temp_dir, "new_dir")
        assert not os.path.exists(test_dir)

        FileUtils.ensure_directory_exists(test_dir)

        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)

    def test_ensure_directory_exists_existing(self, temp_dir):
        # Test with an existing directory
        FileUtils.ensure_directory_exists(temp_dir)
        assert os.path.exists(temp_dir)

    @patch("autoblocks._impl.prompts.v2.discovery.file_utils.os.walk")
    @patch("autoblocks._impl.prompts.v2.discovery.file_utils.shutil.rmtree")
    @patch("autoblocks._impl.prompts.v2.discovery.file_utils.os.remove")
    @patch("autoblocks._impl.prompts.v2.discovery.file_utils.os.path.exists")
    @patch("autoblocks._impl.prompts.v2.discovery.file_utils.log")
    def test_clean_output_directory(self, mock_log, mock_exists, mock_remove, mock_rmtree, mock_walk, temp_dir):
        # Setup mocks
        mock_exists.side_effect = lambda path: path in [
            temp_dir,
            os.path.join(temp_dir, "apps"),
            os.path.join(temp_dir, "__init__.py"),
        ]
        mock_walk.return_value = [
            (temp_dir, ["apps"], ["__init__.py"]),
            (os.path.join(temp_dir, "apps"), ["app1"], []),
            (os.path.join(temp_dir, "apps", "app1"), [], ["__init__.py", "prompts.py"]),
        ]

        # Test cleaning output directory
        FileUtils.clean_output_directory(temp_dir)

        # Check logs
        mock_log.info.assert_called_once_with(f"Cleaning up existing directory: {temp_dir}")
        assert mock_log.debug.call_count == 3  # One for each file

        # Check directory removal
        mock_rmtree.assert_called_once_with(os.path.join(temp_dir, "apps"))

        # Check file removal
        mock_remove.assert_called_once_with(os.path.join(temp_dir, "__init__.py"))

    def test_clean_output_directory_nonexistent(self):
        # Test cleaning a directory that doesn't exist
        with patch("autoblocks._impl.prompts.v2.discovery.file_utils.os.path.exists") as mock_exists:
            mock_exists.return_value = False

            # This should not raise an exception
            FileUtils.clean_output_directory("/nonexistent/dir")

    def test_write_to_file(self, temp_dir):
        # Test writing content to a file
        test_file = os.path.join(temp_dir, "test_dir", "test_file.txt")
        test_content = "Test content"

        # Ensure the parent directory doesn't exist yet
        assert not os.path.exists(os.path.dirname(test_file))

        # Write the file
        FileUtils.write_to_file(test_file, test_content)

        # Check that both the directory and file were created
        assert os.path.exists(os.path.dirname(test_file))
        assert os.path.exists(test_file)

        # Check the file content
        with open(test_file, "r") as f:
            content = f.read()
            assert content == test_content
