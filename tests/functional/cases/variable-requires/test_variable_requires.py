"""Variable / f-string / BinOp + requires and variable tool_requires."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_variable_requires_and_tool_requires_are_extracted():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    assert set(deps.versions) == {"1.0.0", "2.0.0"}

    meta_10 = meta0(deps, "1.0.0", "myrequirement")
    assert meta_10.version == "1.0.1"
    assert meta_10.requires is True

    meta_20 = meta0(deps, "2.0.0", "myrequirement")
    assert meta_20.version == "2.1.0"
    assert meta_20.requires is True

    for v in deps.versions:
        assert "tree-sitter" in deps.deps[v]
        assert meta0(deps, v, "tree-sitter").version == "1.0.0"
        assert "tree-sitter-alt" in deps.deps[v]
        assert meta0(deps, v, "tree-sitter-alt").version == {"1.0.0": "0.1.0", "2.0.0": "0.2.0"}[v]

        assert "cmake" in deps.deps[v]
        assert meta0(deps, v, "cmake").version == "3.15"
        assert meta0(deps, v, "cmake").tool_requires is True
