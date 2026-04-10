"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, functional_profile, meta0

_CASE = Path(__file__).resolve().parent


def test_version_conditionals_branches():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    assert set(deps.versions) == {"1.0.0", "2.0.0", "3.0.0"}
    for v in deps.versions:
        names = deps.deps[v].keys()
        assert "legacy-x" in names
        assert "modern-x" in names
        assert "exact-pin" in names
        assert "gap-pkg" in names
    assert meta0(deps, "1.0.0", "legacy-x").version == "1.0.0"
    assert meta0(deps, "1.0.0", "modern-x").version == "9.9.9"
    assert meta0(deps, "2.0.0", "exact-pin").version == "5.5.5"


def test_compound_not_version_and_only_highest_recipe_version_gets_gap_pkg():
    """(not V < 2.3.5) and (not V < 3.0.0) is True only for 3.0.0 among 1.0.0 / 2.0.0 / 3.0.0."""
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    host = functional_profile("Linux")
    deps.evaluate(None, profile_host=host, profile_build=host)

    assert meta0(deps, "1.0.0", "gap-pkg").default is False
    assert meta0(deps, "2.0.0", "gap-pkg").default is False
    assert meta0(deps, "3.0.0", "gap-pkg").default is True
