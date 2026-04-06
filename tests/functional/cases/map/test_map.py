"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_fstring_conandata_map_and_tool_requires_self_ref():
    """requires(f\"dep-pkg/{conandata map}\") per version; tool_requires(f\"{self.name}/{self.version}\")."""
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    assert set(deps.versions) == {"1.0.0", "2.0.0"}
    meta_10 = meta0(deps, "1.0.0", "dep-pkg")
    assert meta_10.version == "1.0.1"
    meta_20 = meta0(deps, "2.0.0", "dep-pkg")
    assert meta_20.version == "2.1.0"
    for v in deps.versions:
        assert meta0(deps, v, "dep-pkg").requires is True
        tr = meta0(deps, v, "fixture-map")
        assert tr.tool_requires is True
        assert tr.requires is False
        assert tr.version == v
