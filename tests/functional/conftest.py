"""Shared paths and helpers for functional tests (case recipes live under cases/)."""

from pathlib import Path

from conan.internal.model.profile import Profile

_FUNCTIONAL_DIR = Path(__file__).resolve().parent
CASES_ROOT = _FUNCTIONAL_DIR / "cases"
SAMPLE_RECIPES = _FUNCTIONAL_DIR / "assets" / "sample-recipes"


def conanfile_in(case_dir: Path) -> Path:
    """Path to all/conanfile.py inside a CCI-style case folder."""
    return case_dir / "all" / "conanfile.py"


def sample_conanfile_for(recipe_name: str) -> Path:
    """Path to assets/sample-recipes/<recipe>/all/conanfile.py (legacy samples; folder untouched)."""
    return SAMPLE_RECIPES / recipe_name / "all" / "conanfile.py"


def functional_profile(os_s: str, arch: str = "x86_64", conf: dict | None = None) -> Profile:
    p = Profile()
    p.settings = {"os": os_s, "arch": arch}
    p.conf = dict(conf) if conf is not None else {}
    return p


def meta0(deps, recipe_version: str, dep_name: str):
    metas = deps.deps[recipe_version][dep_name]
    assert len(metas) == 1
    return metas[0]


def asio_meta(deps, recipe_version: str, asio_semver: str):
    for m in deps.deps[recipe_version]["mix-asio"]:
        if m.version == asio_semver:
            return m
    raise AssertionError(f"mix-asio/{asio_semver} not found for {recipe_version}")
