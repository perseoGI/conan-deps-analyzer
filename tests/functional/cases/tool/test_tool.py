"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_tool_requires_cmake():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    for version in deps.versions:
        meta = meta0(deps, version, "cmake")
        assert meta.version == "3.15"
        assert meta.requires is False
        assert meta.tool_requires is True
