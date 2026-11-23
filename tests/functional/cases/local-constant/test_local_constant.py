"""Local variable assigned to a string constant and used in several requires."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_local_constant_in_requires():
    deps = extract_conan_dependencies(conanfile_in(_CASE), no_cache=True)
    assert meta0(deps, "1.0.0", "first").version == "1.4.357.0"
    assert meta0(deps, "1.0.0", "second").version == "1.4.357.0"
