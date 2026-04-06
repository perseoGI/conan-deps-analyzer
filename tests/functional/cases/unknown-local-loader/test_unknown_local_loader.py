"""Foo-style local binding: `x = str(self.options...); if x in (...)` is not modeled (UnknownCondition)."""

from pathlib import Path

from parser.condition import UnknownCondition
from parser.dependency_extractor import extract_conan_dependencies

from conftest import conanfile_in, meta0

_CASE = Path(__file__).resolve().parent


def test_local_bound_str_option_membership_is_unknown():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    meta = meta0(deps, "1.0.0", "u-dep")
    assert isinstance(meta.conditions, UnknownCondition)
