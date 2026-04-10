"""Parser gap: compound (not Version<...) and (...) in requirements — evaluator not implemented."""

import pytest
from pathlib import Path

from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, functional_profile, meta0

_CASE = Path(__file__).resolve().parent


@pytest.mark.skip(reason="ConditionEvaluator does not model compound (not Version<...) and (...) yet")
def test_compound_not_version_and_only_3_1_0_gets_gap_pkg():
    """(not V < 2.3.5) and (not V < 3.0.0) is True only for 3.1.0 here."""
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    host = functional_profile("Linux")
    deps.evaluate(None, profile_host=host, profile_build=host)

    m10 = meta0(deps, "1.0.0", "gap-pkg")
    m20 = meta0(deps, "2.0.0", "gap-pkg")
    m31 = meta0(deps, "3.1.0", "gap-pkg")

    assert m10.default is False
    assert m20.default is False
    assert m31.default is True
