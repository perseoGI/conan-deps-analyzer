"""Local variable passed to self.requires() / self.tool_requires(); requires uses f-string + conan_data."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_variable_requires_and_tool_requires_are_extracted():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    assert set(deps.versions) == {"1.0.0", "2.0.0"}

    meta_10 = meta0(deps, "1.0.0", "myrequirement")
    assert meta_10.version == "1.0.1"
    assert meta_10.requires is True

    meta_20 = meta0(deps, "2.0.0", "myrequirement")
    assert meta_20.version == "2.1.0"
    assert meta_20.requires is True

    for version in deps.versions:
        assert "cmake" in deps.deps[version]
        assert meta0(deps, version, "cmake").version == "3.15"
        assert meta0(deps, version, "cmake").tool_requires is True
