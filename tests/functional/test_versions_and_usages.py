"""Functional tests for list versions / list usages over a whole recipes folder."""

import json
import textwrap

import pytest
from conan.errors import ConanException

from conftest import CASES_ROOT
from parser.analyzer import DependenciesAnalyzer


@pytest.fixture
def multi_folder_recipes(tmp_path):
    """A recipe whose versions are split across two folders (all/ and 2.x/)."""
    recipe = tmp_path / "multi"
    recipe.joinpath("config.yml").parent.mkdir(parents=True)
    recipe.joinpath("config.yml").write_text(
        textwrap.dedent(
            """
            versions:
              "2.1.0":
                folder: "2.x"
              "2.0.0":
                folder: "2.x"
              "1.0.0":
                folder: all
            """
        )
    )
    for folder in ("all", "2.x"):
        (recipe / folder).mkdir()
        (recipe / folder / "conandata.yml").write_text("sources: {}\n")
        (recipe / folder / "conanfile.py").write_text(
            "from conan import ConanFile\n\nclass Multi(ConanFile):\n    name = 'multi'\n"
        )
    return tmp_path


def test_versions_counts_every_folder_of_a_recipe(multi_folder_recipes):
    versions = DependenciesAnalyzer(multi_folder_recipes).analyze(no_cache=True).get_versions()
    assert sorted(versions["multi"]) == ["1.0.0", "2.0.0", "2.1.0"]


def test_versions_min_filter_uses_total_count(multi_folder_recipes):
    analyzer = DependenciesAnalyzer(multi_folder_recipes).analyze(no_cache=True)
    assert "multi" in analyzer.get_versions(min_filter=3)
    assert "multi" not in analyzer.get_versions(min_filter=4)


def test_versions_only_referenced_is_json_serializable():
    analyzer = DependenciesAnalyzer(CASES_ROOT).analyze(no_cache=True)
    versions = analyzer.get_versions(only_referenced=True)
    assert versions["map"] == ["2.0.0"]
    json.dumps(versions)


def _as_dicts(usages):
    return {v: {c: [m.to_dict() for m in metas] for c, metas in consumers.items()} for v, consumers in usages.items()}


def test_usages_without_reference_lists_all_recipes():
    analyzer = DependenciesAnalyzer(CASES_ROOT).analyze(no_cache=True)
    usages = analyzer.get_usages()
    assert set(usages) == set(analyzer.dependencies)
    assert _as_dicts(usages["map"]) == _as_dicts(analyzer.get_usages(ref="map")["map"])
    assert set(usages["map"]["2.0.0"]) == {"range-consumer"}


def test_transitive_usages_without_reference_raises():
    analyzer = DependenciesAnalyzer(CASES_ROOT).analyze(no_cache=True)
    with pytest.raises(ConanException, match="Transitive usages require"):
        analyzer.get_usages(transitive=True)


@pytest.fixture
def conditional_recipes(tmp_path):
    """consumer requires liba unconditionally, libb only behind an option disabled by default and
    libc through a version range that matches no published version."""

    def recipe(name, versions, conanfile_body=""):
        folder = tmp_path / name / "all"
        folder.mkdir(parents=True)
        entries = "".join(f'  "{v}":\n    folder: all\n' for v in versions)
        (tmp_path / name / "config.yml").write_text(f"versions:\n{entries}")
        (folder / "conandata.yml").write_text("sources: {}\n")
        (folder / "conanfile.py").write_text(
            f"from conan import ConanFile\n\nclass Recipe(ConanFile):\n    name = '{name}'\n{conanfile_body}"
        )

    recipe("liba", ["1.0"])
    recipe("libb", ["2.0"])
    recipe("libc", ["1.0"])
    recipe(
        "consumer",
        ["1.0"],
        textwrap.indent(
            textwrap.dedent(
                """
                options = {"with_b": [True, False]}
                default_options = {"with_b": False}

                def requirements(self):
                    self.requires("liba/1.0")
                    self.requires("libc/[>=5]")
                    if self.options.with_b:
                        self.requires("libb/2.0")
                """
            ),
            "    ",
        ),
    )
    return tmp_path


def test_versions_only_referenced_only_default_needs_evaluated_conditions(conditional_recipes):
    analyzer = DependenciesAnalyzer(conditional_recipes).analyze(no_cache=True)
    assert analyzer.get_versions(only_referenced=True)["libb"] == ["2.0"]

    analyzer.evaluate(conan_api=None)
    referenced_by_default = analyzer.get_versions(only_referenced=True, only_default=True, min_filter=1)
    assert referenced_by_default == {"liba": ["1.0"]}


def test_versions_only_referenced_skips_unresolved_ranges(conditional_recipes):
    versions = DependenciesAnalyzer(conditional_recipes).analyze(no_cache=True).get_versions(only_referenced=True)
    assert versions["libc"] == []
    assert "None" not in json.dumps(versions)
