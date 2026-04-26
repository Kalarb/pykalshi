"""Shared test fixtures."""

import pytest
from pykalshi.testing.fixtures import mock_credentials, test_config as _test_config
from pykalshi.auth import KalshiCredentials
from pykalshi.config import ClientConfig


@pytest.fixture
def credentials() -> KalshiCredentials:
    return mock_credentials()


@pytest.fixture
def config() -> ClientConfig:
    return _test_config()
