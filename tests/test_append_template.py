"""Tests for pyproject.toml template functionality."""
import os
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.testing import TestBase


class TestPyprojectTemplate(TestBase):
    """Test the pyproject template, particularly issue #1679."""
    
    def test_init_pyproject_existing_file_formatting(self):
        """Test that appending to existing pyproject.toml maintains proper spacing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            
            # Create existing pyproject.toml
            pyproject_path = Path("pyproject.toml")
            pyproject_path.write_text(
                '[tool.black]\ntarget-version = [\'py37\']\n\n'
                '[tool.mypy]\npython_version = "3.10"'
            )
            
            # Run init
            config = Config("pyproject.toml")
            command.init(config, "alembic", template="pyproject")
            
            # Check result
            result = pyproject_path.read_text()
            
            # Verify no concatenation (issue #1679)
            assert 'python_version = "3.10"[tool.alembic]' not in result
            
            # Verify proper spacing
            assert '\n\n[tool.alembic]' in result
            
            # Verify content preserved
            assert '[tool.black]' in result
            assert '[tool.mypy]' in result