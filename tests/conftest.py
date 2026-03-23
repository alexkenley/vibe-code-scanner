"""Shared test fixtures."""

from pathlib import Path

import pytest

TEST_APPS_DIR = Path(__file__).parent.parent / "test-apps"


@pytest.fixture
def test_apps_dir():
    return TEST_APPS_DIR


@pytest.fixture
def python_test_app():
    return TEST_APPS_DIR / "python-test-app"


@pytest.fixture
def js_test_app():
    return TEST_APPS_DIR / "js-test-app"


@pytest.fixture
def typescript_test_app():
    return TEST_APPS_DIR / "typescript-test-app"


@pytest.fixture
def supabase_test_app():
    return TEST_APPS_DIR / "supabase-test-app"
