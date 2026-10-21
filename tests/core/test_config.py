"""The gateway configuration: read from the process environment, fail closed when absent."""

from __future__ import annotations

import pytest

from repo_presenter.core.config import (
    API_KEY_VARIABLE,
    ENDPOINT_VARIABLE,
    MODEL_VARIABLE,
    load_gateway_config,
)
from repo_presenter.core.errors import ConfigError


def test_both_variables_present_resolves_a_config() -> None:
    config = load_gateway_config(
        {ENDPOINT_VARIABLE: "https://gateway.example/v1/", API_KEY_VARIABLE: "sk-test"}
    )
    assert config.base_url == "https://gateway.example/v1"  # trailing slash stripped
    assert config.api_key == "sk-test"
    assert config.host == "gateway.example"
    assert config.model_override is None


def test_the_optional_model_override_is_read_when_present() -> None:
    config = load_gateway_config(
        {
            ENDPOINT_VARIABLE: "https://gateway.example/v1",
            API_KEY_VARIABLE: "sk-test",
            MODEL_VARIABLE: "qwen3-next",
        }
    )
    assert config.model_override == "qwen3-next"


def test_missing_both_variables_fails_closed() -> None:
    with pytest.raises(ConfigError, match=f"{ENDPOINT_VARIABLE} and {API_KEY_VARIABLE}"):
        load_gateway_config({})


def test_missing_only_the_api_key_names_it() -> None:
    with pytest.raises(ConfigError, match=API_KEY_VARIABLE):
        load_gateway_config({ENDPOINT_VARIABLE: "https://gateway.example/v1"})


def test_a_non_http_endpoint_is_rejected() -> None:
    with pytest.raises(ConfigError, match="absolute http"):
        load_gateway_config({ENDPOINT_VARIABLE: "not-a-url", API_KEY_VARIABLE: "sk-test"})


def test_this_environment_actually_carries_the_two_required_variables() -> None:
    """This taskcard's own finding (see core/llm/jobs.py's module docstring): confirmed by
    environment-variable NAME only, values never read, logged or asserted against."""
    import os

    assert ENDPOINT_VARIABLE in os.environ, f"{ENDPOINT_VARIABLE} is not set in this environment"
    assert API_KEY_VARIABLE in os.environ, f"{API_KEY_VARIABLE} is not set in this environment"
