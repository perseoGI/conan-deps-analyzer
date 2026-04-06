"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_options_dict_expansion_and_option_conditionals():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    for v in deps.versions:
        assert "audio-dep" in deps.deps[v]
        assert "no-video-dep" in deps.deps[v]
    assert meta0(deps, "1.0.0", "audio-dep").version == "1.0.0"
    assert meta0(deps, "1.0.0", "no-video-dep").version == "2.0.0"
