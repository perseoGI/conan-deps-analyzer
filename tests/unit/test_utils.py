import textwrap
from pathlib import Path

import pytest
from conan.errors import ConanException

from parser.utils import (
    get_available_versions_from_config,
    is_version_range,
    missing_binaries_breaking_minor_line,
    version_range_intersects,
)


def test_is_version_range_true():
    assert is_version_range("[>=1.0 <2.0]") is True


def test_is_version_range_false_plain_version():
    assert is_version_range("1.2.3") is False


def test_is_version_range_false_partial_brackets():
    assert is_version_range("[1.2.3") is False


def test_get_available_versions_from_config_parses_and_sorts_desc(tmp_path: Path):
    config = tmp_path / "config.yml"
    config.write_text(
        textwrap.dedent(
            """
            versions:
              "1.0.0":
                folder: all
              "2.1.0":
                folder: all
            """
        ).strip(),
        encoding="utf-8",
    )
    versions = get_available_versions_from_config(config, folder="all")
    assert [str(v) for v in versions] == ["2.1.0", "1.0.0"]


def test_get_available_versions_from_config_filters_by_folder(tmp_path: Path):
    config = tmp_path / "config.yml"
    config.write_text(
        textwrap.dedent(
            """
            versions:
              "1.0.0":
                folder: all
              "3.0.0":
                folder: v3
            """
        ).strip(),
        encoding="utf-8",
    )
    only_all = get_available_versions_from_config(config, folder="all")
    assert [str(v) for v in only_all] == ["1.0.0"]


def test_get_available_versions_from_config_empty_or_missing_versions(tmp_path: Path):
    empty = tmp_path / "empty.yml"
    empty.write_text("{}", encoding="utf-8")
    assert get_available_versions_from_config(empty) == []

    no_versions = tmp_path / "no_versions.yml"
    no_versions.write_text("other: 1\n", encoding="utf-8")
    assert get_available_versions_from_config(no_versions) == []


def test_get_available_versions_from_config_invalid_yaml(tmp_path: Path):
    bad = tmp_path / "bad.yml"
    bad.write_text("versions: [\n", encoding="utf-8")
    with pytest.raises(ConanException, match="Error parsing YAML"):
        get_available_versions_from_config(bad)


def test_version_range_intersects_overlapping():
    assert version_range_intersects("[>=1.0 <3.0]", "[>=2.0 <4.0]") is True


def test_version_range_intersects_disjoint():
    assert version_range_intersects("[>=1.0 <2.0]", "[>=3.0 <4.0]") is False


# --- missing_binaries_breaking_minor_line tests ---


def test_missing_binaries_same_minor_no_break():
    # 2.14.3 -> 2.14.6: same minor line, no break
    assert missing_binaries_breaking_minor_line("2.14.3", "2.14.6", "2.14.3") is False


def test_missing_binaries_different_minor_breaks():
    # 2.14.3 -> 2.15.0: different minor line, breaks
    assert missing_binaries_breaking_minor_line("2.14.3", "2.15.0", "2.14.3") is True


def test_missing_binaries_different_major_breaks():
    # 2.14.3 -> 3.0.0: different major, breaks
    assert missing_binaries_breaking_minor_line("2.14.3", "3.0.0", "2.14.3") is True


def test_missing_binaries_resolved_none_uses_latest():
    # No resolved version, uses latest_published as baseline
    assert missing_binaries_breaking_minor_line(None, "2.15.0", "2.14.3") is True
    assert missing_binaries_breaking_minor_line(None, "2.14.5", "2.14.3") is False


def test_missing_binaries_empty_baseline_returns_true():
    # Empty baseline means we can't compare, assume break
    assert missing_binaries_breaking_minor_line(None, "1.0.0", "") is True
    assert missing_binaries_breaking_minor_line("", "1.0.0", "") is True
