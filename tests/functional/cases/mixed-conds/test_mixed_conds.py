"""CCI-shaped recipe colocated with this module; exercised by extract_conan_dependencies."""

from pathlib import Path

import pytest

from parser.dependency_extractor import extract_conan_dependencies

from conftest import asio_meta, conanfile_in, functional_profile, meta0

_CASE = Path(__file__).resolve().parent


def test_mixed_conds_extracts_version_zlib_os_and_helpers():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    assert set(deps.versions) == {"1.0.0", "3.0.0"}
    for v in deps.versions:
        names = deps.deps[v].keys()
        assert {
            "mix-asio",
            "mix-nolib-low",
            "mix-nolib-high",
            "mix-cross-safe",
            "mix-droid",
            "mix-msvc",
            "mix-apple",
            "mix-win-gnu",
            "mix-wt",
            "mix-jpeg-inline",
            "mix-odbc",
            "mix-posix",
        } <= names

    assert asio_meta(deps, "1.0.0", "1.16.1").version == "1.16.1"
    assert asio_meta(deps, "1.0.0", "1.28.1").version == "1.28.1"
    assert asio_meta(deps, "3.0.0", "1.16.1").version == "1.16.1"
    assert asio_meta(deps, "3.0.0", "1.28.1").version == "1.28.1"

    assert meta0(deps, "1.0.0", "mix-jpeg-inline").version == "3.0.2"


@pytest.mark.parametrize(
    "host_os,expect_msvc,expect_apple,expect_posix,expect_win_gnu",
    [
        ("Linux", False, False, True, False),
        ("Windows", True, False, False, True),
        ("Macos", False, True, True, False),
    ],
)
def test_mixed_conds_evaluate_os_profiles(host_os, expect_msvc, expect_apple, expect_posix, expect_win_gnu):
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    host = functional_profile(host_os)
    deps.evaluate(None, profile_host=host, profile_build=host)
    v = "1.0.0"
    assert meta0(deps, v, "mix-msvc").default is expect_msvc
    assert meta0(deps, v, "mix-apple").default is expect_apple
    assert meta0(deps, v, "mix-posix").default is expect_posix
    assert meta0(deps, v, "mix-win-gnu").default is expect_win_gnu
    assert meta0(deps, v, "mix-odbc").default is True


def test_mixed_conds_evaluate_android():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    host = functional_profile("Android", arch="armv8")
    deps.evaluate(None, profile_host=host, profile_build=host)
    assert meta0(deps, "1.0.0", "mix-droid").default is True


def test_mixed_conds_evaluate_cross_build_flips_cross_safe():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    host = functional_profile("Linux")
    build = functional_profile("Windows")
    deps.evaluate(None, profile_host=host, profile_build=build)
    assert meta0(deps, "1.0.0", "mix-cross-safe").default is False

    deps2 = extract_conan_dependencies(path, no_cache=True)
    h = functional_profile("Linux")
    deps2.evaluate(None, profile_host=h, profile_build=h)
    assert meta0(deps2, "1.0.0", "mix-cross-safe").default is True


def test_mixed_conds_evaluate_conf_bash_path():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    host = functional_profile("Linux", conf={"tools.microsoft.bash:path": "/usr/bin/bash"})
    deps.evaluate(None, profile_host=host, profile_build=host)
    assert meta0(deps, "1.0.0", "mix-wt").default is False

    deps2 = extract_conan_dependencies(path, no_cache=True)
    host2 = functional_profile("Linux", conf={})
    deps2.evaluate(None, profile_host=host2, profile_build=host2)
    assert meta0(deps2, "1.0.0", "mix-wt").default is True


def test_mixed_conds_evaluate_version_zlib_branch_defaults():
    path = conanfile_in(_CASE)
    deps = extract_conan_dependencies(path, no_cache=True)
    host = functional_profile("Linux")
    deps.evaluate(None, profile_host=host, profile_build=host)
    assert asio_meta(deps, "1.0.0", "1.16.1").default is True
    assert asio_meta(deps, "1.0.0", "1.28.1").default is None
    assert asio_meta(deps, "3.0.0", "1.28.1").default is True
    assert asio_meta(deps, "3.0.0", "1.16.1").default is None
