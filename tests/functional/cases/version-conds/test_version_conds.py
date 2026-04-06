"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

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
    assert meta0(deps, "1.0.0", "legacy-x").version == "1.0.0"
    assert meta0(deps, "1.0.0", "modern-x").version == "9.9.9"
    assert meta0(deps, "2.0.0", "exact-pin").version == "5.5.5"
