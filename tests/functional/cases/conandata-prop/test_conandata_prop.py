"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_conandata_property_fstring():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    assert set(deps.versions) == {"1.0.0", "2.0.0"}
    assert meta0(deps, "1.0.0", "sidecar").version == "1.5.0"
    assert meta0(deps, "2.0.0", "sidecar").version == "2.6.0"
