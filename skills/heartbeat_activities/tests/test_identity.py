"""
Tests for identity helper (identity.py).

Covers: extract_primary_name — name found, name missing, malformed file.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from heartbeat_activities.identity import extract_primary_name


@pytest.fixture
def tmp_workspace(tmp_path):
    return tmp_path


def test_extracts_name_from_h1(tmp_workspace):
    path = tmp_workspace / "USER.md"
    path.write_text("# {{USER_NAME}}\n\nSome description", encoding="utf-8")
    assert extract_primary_name(tmp_workspace) == "{{USER_NAME}}"


def test_extracts_name_mari(tmp_workspace):
    path = tmp_workspace / "USER.md"
    path.write_text("# Mari\n\nMy name is Mari", encoding="utf-8")
    assert extract_primary_name(tmp_workspace) == "Mari"


def test_returns_empty_when_no_file(tmp_workspace):
    result = extract_primary_name(tmp_workspace)
    assert result == ""


def test_returns_empty_when_no_h1(tmp_workspace):
    path = tmp_workspace / "USER.md"
    path.write_text("Just some text without a heading", encoding="utf-8")
    result = extract_primary_name(tmp_workspace)
    assert result == ""


def test_returns_empty_when_malformed_json(tmp_workspace):
    path = tmp_workspace / "USER.md"
    path.write_text("not valid json{{{", encoding="utf-8")
    result = extract_primary_name(tmp_workspace)
    assert result == ""


def test_first_h1_wins(tmp_workspace):
    path = tmp_workspace / "USER.md"
    path.write_text("# First\n\n## Second\n\n# Third", encoding="utf-8")
    result = extract_primary_name(tmp_workspace)
    assert result == "First"


def test_name_is_stripped(tmp_workspace):
    path = tmp_workspace / "USER.md"
    path.write_text("#   {{USER_NAME}}   \n\nExtra whitespace", encoding="utf-8")
    result = extract_primary_name(tmp_workspace)
    assert result == "{{USER_NAME}}"


def test_custom_user_file(tmp_workspace):
    path = tmp_workspace / "IDENTITY.md"
    path.write_text("# {{AGENT_NAME}}\n\nSomething", encoding="utf-8")
    result = extract_primary_name(tmp_workspace, user_file="IDENTITY.md")
    assert result == "{{AGENT_NAME}}"
