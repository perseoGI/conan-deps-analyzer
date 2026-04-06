"""CCI-shaped recipe colocated with this module; version ranges resolve against other case recipes in cases/."""

from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_single_version_per_dependency_resolved_from_ranges():
    """One require per dependency; each range picks the highest matching version from the sibling case config."""
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    v = "1.0.0"
    m_map = meta0(deps, v, "map")
    assert m_map.version == "2.0.0"
    assert m_map.version_range == "[>=1.5 <3]"

    m_pf = meta0(deps, v, "property-fstring")
    assert m_pf.version == "3.0.0"
    assert m_pf.version_range == "[>=2.5 <4]"

    m_vc = meta0(deps, v, "version-conds")
    assert m_vc.version == "2.0.0"
    assert m_vc.version_range == "[>=1.5 <3]"
