"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in

_CASE = Path(__file__).resolve().parent


def test_host_version_tool_requires_separate_meta():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    for v in deps.versions:
        metas = deps.deps[v]["codec"]
        assert len(metas) == 2
        versions = {m.version for m in metas}
        assert "2.0.0" in versions
        assert "<host_version>" in versions
        by_ver = {m.version: m for m in metas}
        assert by_ver["2.0.0"].requires is True
        assert by_ver["2.0.0"].tool_requires is False
        assert by_ver["<host_version>"].tool_requires is True
