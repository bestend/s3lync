"""
Pytest configuration.
"""

import os
import tempfile

import pytest

# Configure pytest-asyncio to use auto mode for async tests
pytest_plugins = ["pytest_asyncio"]


@pytest.fixture
def temp_dir():
    """Temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_file():
    """Temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
        f.write("test content")
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)
