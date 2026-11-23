"""self.conan_data[key][self.version][subkey] stored in a local variable."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_conandata_nested_local_variable():
    deps = extract_conan_dependencies(conanfile_in(_CASE), no_cache=True)
    assert set(deps.versions) == {"1.0.0", "2.0.0"}
    assert meta0(deps, "1.0.0", "sidecar").version == "1.5.0"
    assert meta0(deps, "2.0.0", "sidecar").version == "2.6.0"
