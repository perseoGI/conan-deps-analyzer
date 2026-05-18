"""Functional tests for the missing-binaries command."""

import pytest
from conan.errors import ConanException

from conftest import CASES_ROOT
from parser.analyzer import DependenciesAnalyzer


def test_missing_binaries_new_minor_version_breaks():
    """A new minor version (2.0 -> 2.1) should cause missing binaries."""
    analyzer = DependenciesAnalyzer(CASES_ROOT).analyze(no_cache=True)
    
    # map has 1.0.0 and 2.0.0 published
    # Hypothetical map/2.1.0 would break consumers resolving to 2.0.0 (range-consumer uses map/[>=1.5 <3])
    result = analyzer.get_missing_binaries(ref="map/2.1.0", only_default=False)
    
    assert len(result) > 0
    consumers = [r["consumer"] for r in result]
    assert any("range-consumer" in c for c in consumers)


def test_missing_binaries_same_minor_no_break():
    """A patch version (2.0.0 -> 2.0.1) should NOT cause missing binaries."""
    analyzer = DependenciesAnalyzer(CASES_ROOT).analyze(no_cache=True)
    
    # map/2.0.1 is same minor line as existing 2.0.0
    result = analyzer.get_missing_binaries(ref="map/2.0.1", only_default=False)
    
    # Should be empty since 2.0.1 is same minor line as 2.0.0
    range_consumer_results = [r for r in result if "range-consumer" in r["consumer"]]
    assert len(range_consumer_results) == 0


def test_missing_binaries_ref_without_version_raises():
    """Reference without version should raise ConanException."""
    analyzer = DependenciesAnalyzer(CASES_ROOT).analyze(no_cache=True)
    
    with pytest.raises(ConanException, match="must include version"):
        analyzer.get_missing_binaries(ref="map", only_default=False)
