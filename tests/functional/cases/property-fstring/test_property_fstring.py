"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_property_dict_fstring_per_version():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    assert set(deps.versions) == {"1.0.0", "2.0.0", "3.0.0"}
    assert meta0(deps, "1.0.0", "bx-lib").version == "10.1.0"
    assert meta0(deps, "2.0.0", "bx-lib").version == "20.2.0"
    assert meta0(deps, "3.0.0", "bx-lib").version == "30.3.0"
