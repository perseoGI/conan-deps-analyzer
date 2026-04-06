"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in

_CASE = Path(__file__).resolve().parent


def test_same_version_requires_and_tool_requires_merge():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    for v in deps.versions:
        metas = deps.deps[v]["cmake"]
        assert len(metas) == 1
        assert metas[0].version == "3.20"
        assert metas[0].requires is True
        assert metas[0].tool_requires is True
