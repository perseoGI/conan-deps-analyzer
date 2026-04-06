"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_min_extracts_literal_require_for_all_versions():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    assert set(deps.versions) == {"1.0.0"}
    for version in deps.versions:
        assert set(deps.deps[version].keys()) == {"tree-sitter"}
        meta = meta0(deps, version, "tree-sitter")
        assert meta.version == "1.0.0"
        assert meta.requires is True
        assert meta.tool_requires is False
        assert meta.version_range is None
