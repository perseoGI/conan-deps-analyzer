import ast

import pytest
from conan.tools.scm import Version

from parser.condition import (
    AndCondition,
    ConstantCondition,
    NoCondition,
    OrCondition,
    VersionCondition,
)


def test_no_condition_evaluates_true():
    assert NoCondition().evaluate() is True


def test_no_condition_and_absorbs_other():
    c = ConstantCondition(True)
    assert isinstance(NoCondition() & c, ConstantCondition)


def test_no_condition_or_returns_other():
    c = ConstantCondition(False)
    assert isinstance(NoCondition() | c, ConstantCondition)


def test_constant_condition_evaluate():
    assert ConstantCondition(True).evaluate() is True
    assert ConstantCondition(False).evaluate() is False


def test_constant_condition_invert():
    c = ConstantCondition(True)
    assert (~c).evaluate() is False


def test_version_condition_evaluate():
    vc = VersionCondition({Version("1.0"): True, Version("2.0"): False})
    assert vc.evaluate(version="1.0") is True
    assert vc.evaluate(version="2.0") is False


def test_and_condition_all_must_hold():
    a = AndCondition(ConstantCondition(True), ConstantCondition(True))
    assert a.evaluate() is True
    b = AndCondition(ConstantCondition(True), ConstantCondition(False))
    assert b.evaluate() is False


def test_or_condition_any_holds():
    a = OrCondition(ConstantCondition(False), ConstantCondition(True))
    assert a.evaluate() is True
    b = OrCondition(ConstantCondition(False), ConstantCondition(False))
    assert b.evaluate() is False


def test_profile_dependent_default_settings_os_match():
    from parser.condition import ProfileDependentCondition
    from conan.internal.model.profile import Profile

    host = Profile()
    host.settings = {"os": "Linux"}
    cond = ProfileDependentCondition(admited_settings={"os": "Linux"}, operator=ast.Eq)
    assert cond.evaluate(profile_host=host, profile_build=None) is True


def test_profile_dependent_cross_building_requires_both_profiles():
    from parser.condition import ProfileDependentCondition
    from conan.internal.model.profile import Profile

    cond = ProfileDependentCondition(check_cross_building=True)
    assert cond.evaluate(profile_host=None, profile_build=None) is True

    host = Profile()
    host.settings = {"os": "Linux", "arch": "x86_64"}
    build = Profile()
    build.settings = {"os": "Linux", "arch": "x86_64"}
    assert cond.evaluate(profile_host=host, profile_build=build) is False
