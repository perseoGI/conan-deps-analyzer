"""Functional tests for the compact output format (space-separated references)."""

from conftest import CASES_ROOT
from parser.analyzer import DependenciesAnalyzer
from parser.output import print_missing_binaries_compact, print_usages_compact


def _analyzer():
    return DependenciesAnalyzer(CASES_ROOT).analyze(no_cache=True)


def test_usages_compact_single_line_sorted_unique(capsys):
    usages = _analyzer().get_usages(ref="map", only_default=False)
    print_usages_compact(usages)
    out = capsys.readouterr().out
    assert out.count("\n") == 1
    refs = out.split()
    assert refs == sorted(set(refs))
    assert "range-consumer/1.0.0" in refs


def test_usages_compact_empty_prints_nothing(capsys):
    usages = _analyzer().get_usages(ref="range-consumer", only_default=False)
    print_usages_compact(usages)
    assert capsys.readouterr().out == ""


def test_missing_binaries_compact(capsys):
    result = _analyzer().get_missing_binaries(ref="map/2.1.0", only_default=False)
    print_missing_binaries_compact(result)
    assert capsys.readouterr().out.split() == ["range-consumer/1.0.0"]


def test_missing_binaries_compact_empty_prints_nothing(capsys):
    result = _analyzer().get_missing_binaries(ref="map/2.0.1", only_default=False)
    print_missing_binaries_compact(result)
    assert capsys.readouterr().out == ""


def test_missing_binaries_compact_deduplicates(capsys):
    item = {"consumer": "b", "consumer_version": "1.0"}
    print_missing_binaries_compact([item, {"consumer": "a", "consumer_version": "2.0"}, item])
    assert capsys.readouterr().out == "a/2.0 b/1.0\n"
