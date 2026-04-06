"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_conditional_require_when_option_true():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    for version in deps.versions:
        assert set(deps.deps[version].keys()) == {"extra-pkg"}
        meta = meta0(deps, version, "extra-pkg")
        assert meta.version == "1.0.0"
        assert meta.requires is True
