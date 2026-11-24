"""analyze() in worker processes must give the same result as the sequential path, and fill the cache."""

import pytest
from conan.errors import ConanException

from conftest import CASES_ROOT
from parser import analyzer as analyzer_module
from parser import utils
from parser.analyzer import DependenciesAnalyzer, _parallel_jobs
from parser.dependency_extractor import extract_conan_dependencies


def _snapshot(analyzer):
    return {
        recipe: [
            {v: {d: [m.to_dict() for m in metas] for d, metas in deps.items()} for v, deps in rd.deps.items()}
            for rd in recipe_deps
        ]
        for recipe, recipe_deps in analyzer.dependencies.items()
    }


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    cache = utils._PersistentCache(tmp_path / "cache.pickle")
    monkeypatch.setattr(utils, "_CACHE", cache)
    return cache


def test_parallel_matches_sequential_and_fills_cache(monkeypatch, isolated_cache):
    monkeypatch.setenv("CCI_PARSER_JOBS", "1")
    sequential = _snapshot(DependenciesAnalyzer(CASES_ROOT).analyze(no_cache=True))

    isolated_cache._entries = {}
    monkeypatch.setattr(analyzer_module, "_PARALLEL_MIN_RECIPES", 1)
    monkeypatch.setenv("CCI_PARSER_JOBS", "2")
    parallel_analyzer = DependenciesAnalyzer(CASES_ROOT).analyze(no_cache=True)
    assert _snapshot(parallel_analyzer) == sequential

    # Workers' results were stored by the parent, with the files they depended on
    for path in parallel_analyzer.recipe_paths:
        assert extract_conan_dependencies.lookup(path) is not utils.MISS


def test_parallel_jobs(monkeypatch):
    monkeypatch.delenv("CCI_PARSER_JOBS", raising=False)
    assert _parallel_jobs(analyzer_module._PARALLEL_MIN_RECIPES - 1) == 1
    assert 1 <= _parallel_jobs(10_000) <= analyzer_module._MAX_DEFAULT_JOBS
    monkeypatch.setenv("CCI_PARSER_JOBS", "3")
    assert _parallel_jobs(10_000) == 3
    monkeypatch.setenv("CCI_PARSER_JOBS", "many")
    with pytest.raises(ConanException, match="CCI_PARSER_JOBS"):
        _parallel_jobs(10_000)


def test_cache_from_other_code_version_is_discarded(tmp_path, monkeypatch):
    path = tmp_path / "cache.pickle"
    cache = utils._PersistentCache(path)
    cache.set("key", {"value": 1})
    cache.flush()
    assert utils._PersistentCache(path).get("key") == {"value": 1}

    monkeypatch.setattr(utils._PersistentCache, "_code_fingerprint", staticmethod(lambda: "other-version"))
    assert utils._PersistentCache(path).get("key") is None
