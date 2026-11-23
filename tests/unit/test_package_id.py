import pytest

from parser.package_id import (
    clears_requires_in_package_id,
    get_declared_package_id_modes,
    get_effective_mode,
    version_change_affects_package_id,
)


@pytest.mark.parametrize(
    "mode,old,new,expected",
    [
        ("major_mode", "1.2.3", "1.9.0", False),
        ("major_mode", "1.2.3", "2.0.0", True),
        ("semver_mode", "1.2.3", "1.9.0", False),
        ("semver_mode", "0.1.3", "0.1.9", False),
        ("semver_mode", "0.1.3", "0.2.0", True),
        ("minor_mode", "1.2.3", "1.2.9", False),
        ("minor_mode", "1.2.3", "1.3.0", True),
        ("patch_mode", "1.2.3", "1.2.3", False),
        ("patch_mode", "1.2.3", "1.2.4", True),
        ("full_mode", "1.2.3", "1.2.3.1", True),
    ],
)
def test_version_change_affects_package_id(mode, old, new, expected):
    assert version_change_affects_package_id(mode, old, new) is expected


def test_declared_and_effective_mode(tmp_path):
    f = tmp_path / "conanfile.py"
    f.write_text(
        "from conan import ConanFile\n"
        "class P(ConanFile):\n"
        "    package_id_embed_mode = 'minor_mode'\n"
        "    package_id_non_embed_mode = 'patch_mode'\n"
    )
    assert get_declared_package_id_modes(f) == {
        "package_id_embed_mode": "minor_mode",
        "package_id_non_embed_mode": "patch_mode",
    }
    assert get_effective_mode(f) == "patch_mode"


def test_effective_mode_default(tmp_path):
    f = tmp_path / "conanfile.py"
    f.write_text("from conan import ConanFile\nclass P(ConanFile):\n    pass\n")
    assert get_effective_mode(f) == "minor_mode"


def test_clears_requires_only_when_unconditional(tmp_path):
    uncond = tmp_path / "a.py"
    uncond.write_text("class P:\n    def package_id(self):\n        self.info.requires.clear()\n")
    cond = tmp_path / "b.py"
    cond.write_text(
        "class P:\n    def package_id(self):\n        if self.options.header_only:\n            self.info.requires.clear()\n"
    )
    assert clears_requires_in_package_id(uncond) is True
    assert clears_requires_in_package_id(cond) is False
