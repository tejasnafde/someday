"""Tests for the SOMEDAY_CONFIG blob expansion in config/settings.py.

The blob replaces eight per-value Secret Manager entries with one JSON object,
because Secret Manager bills per secret version rather than per byte. If this
expansion breaks, the service cannot start, so it is worth a test.

These call load_config_blob() directly rather than reimporting the module,
because Settings() runs at import time and the test suite has already imported
it via conftest.
"""

import json
import os

import pytest

from config.settings import load_config_blob


@pytest.fixture
def clean_env(monkeypatch):
    """Isolate the keys these tests touch."""
    for key in ("SOMEDAY_CONFIG", "BLOB_ONLY_KEY", "ALREADY_SET_KEY"):
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_expands_blob_into_environ(clean_env):
    clean_env.setenv("SOMEDAY_CONFIG", json.dumps({"BLOB_ONLY_KEY": "from-blob"}))
    load_config_blob()
    assert os.environ["BLOB_ONLY_KEY"] == "from-blob"


def test_existing_env_var_wins(clean_env):
    """The blob must not clobber an explicitly set value.

    This is what keeps the migration reversible: a per-secret ref or a locally
    exported value still overrides the blob.
    """
    clean_env.setenv("ALREADY_SET_KEY", "explicit")
    clean_env.setenv("SOMEDAY_CONFIG", json.dumps({"ALREADY_SET_KEY": "from-blob"}))
    load_config_blob()
    assert os.environ["ALREADY_SET_KEY"] == "explicit"


def test_absent_blob_is_a_no_op(clean_env):
    """Local dev and the test suite set no blob, and must still work."""
    load_config_blob()
    assert "SOMEDAY_CONFIG" not in os.environ


def test_empty_blob_is_a_no_op(clean_env):
    clean_env.setenv("SOMEDAY_CONFIG", "")
    load_config_blob()


def test_malformed_blob_raises(clean_env):
    """Fail loudly, not silently.

    A crash at import means Cloud Run refuses to shift traffic to the new
    revision, so the previous one keeps serving. Swallowing this would start a
    service with missing credentials that fails per-request instead.
    """
    clean_env.setenv("SOMEDAY_CONFIG", "{not json")
    with pytest.raises(json.JSONDecodeError):
        load_config_blob()


def test_non_string_values_are_coerced(clean_env):
    """Env vars must be strings; a JSON number would otherwise break putenv."""
    clean_env.setenv("SOMEDAY_CONFIG", json.dumps({"BLOB_ONLY_KEY": 8080}))
    load_config_blob()
    assert os.environ["BLOB_ONLY_KEY"] == "8080"
