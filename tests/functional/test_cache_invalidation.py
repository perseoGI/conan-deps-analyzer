"""The persistent parse cache must be invalidated when any YAML file the result depends on changes."""

import os
import shutil

import pytest

from conftest import CASES_ROOT
from parser import utils
from parser.dependency_extractor import extract_conan_dependencies


@pytest.fixture
def recipes(tmp_path, monkeypatch):
    """Copy of the cases needed by range-consumer, with an isolated cache database."""
    monkeypatch.setattr(utils, "CACHE_DB_PATH", tmp_path / "cache_db")
    root = tmp_path / "recipes"
    for case in ("range-consumer", "map", "property-fstring", "version-conds"):
        shutil.copytree(CASES_ROOT / case, root / case, ignore=shutil.ignore_patterns("__pycache__", "*.py[co]"))
    yield root
    utils._get_available_versions_from_config.cache_clear()
    utils._get_conandata.cache_clear()


def _extract(conanfile):
    # lru caches would hide on-disk changes within one process, so drop them as a new run would
    utils._get_available_versions_from_config.cache_clear()
    utils._get_conandata.cache_clear()
    return extract_conan_dependencies(conanfile, no_cache=False)


def _bump_mtime(path):
    st = path.stat()
    os.utime(path, (st.st_atime, st.st_mtime + 10))


def test_cache_invalidated_when_dependency_config_changes(recipes):
    conanfile = recipes / "range-consumer" / "all" / "conanfile.py"
    assert _extract(conanfile).deps["1.0.0"]["map"][0].version == "2.0.0"

    map_config = recipes / "map" / "config.yml"
    map_config.write_text(map_config.read_text() + '  "2.5.0":\n    folder: all\n')
    _bump_mtime(map_config)

    assert _extract(conanfile).deps["1.0.0"]["map"][0].version == "2.5.0"


def test_cache_invalidated_when_own_config_changes(recipes):
    conanfile = recipes / "range-consumer" / "all" / "conanfile.py"
    assert _extract(conanfile).versions == ["1.0.0"]

    config = recipes / "range-consumer" / "config.yml"
    config.write_text(config.read_text() + '  "1.1.0":\n    folder: all\n')
    _bump_mtime(config)

    assert _extract(conanfile).versions == ["1.1.0", "1.0.0"]


def test_cache_hit_when_nothing_changes(recipes, monkeypatch):
    conanfile = recipes / "range-consumer" / "all" / "conanfile.py"
    first = _extract(conanfile)

    def fail(*_args, **_kwargs):
        raise AssertionError("recipe was parsed again instead of served from cache")

    monkeypatch.setattr("parser.dependency_extractor.RecipeVisitor", fail)
    assert _extract(conanfile).deps.keys() == first.deps.keys()
