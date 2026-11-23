"""Static inspection of how a recipe affects the package_id of its consumers."""

import ast
from functools import lru_cache
from pathlib import Path

from conan.tools.scm import Version

MODE_ATTRIBUTES = ("package_id_embed_mode", "package_id_non_embed_mode", "package_id_unknown_mode")
# Conan default when nothing is declared: assume the dependency is not embedded (minor_mode)
DEFAULT_MODE = "minor_mode"
# From least to most sensitive to version changes
_MODE_ORDER = ["major_mode", "semver_mode", "minor_mode", "patch_mode", "full_mode", "recipe_revision_mode"]


def _class_nodes(conanfile_path: Path):
    tree = ast.parse(Path(conanfile_path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield node


@lru_cache(maxsize=None)
def get_declared_package_id_modes(conanfile_path: Path) -> dict:
    """package_id_*_mode attributes declared as string constants in the recipe class."""
    modes = {}
    for cls in _class_nodes(conanfile_path):
        for stmt in cls.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and stmt.targets[0].id in MODE_ATTRIBUTES
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                modes[stmt.targets[0].id] = stmt.value.value
    return modes


def get_effective_mode(conanfile_path: Path) -> str:
    """
    Mode used to decide whether a new dependency version changes consumers' package_id.
    Whether the dependency is embedded or not can't be known statically, so when several
    modes are declared the most sensitive one wins; with none declared, DEFAULT_MODE.
    """
    declared = [m for m in get_declared_package_id_modes(conanfile_path).values() if m in _MODE_ORDER]
    if not declared:
        return DEFAULT_MODE
    return max(declared, key=_MODE_ORDER.index)


@lru_cache(maxsize=None)
def clears_requires_in_package_id(conanfile_path: Path) -> bool:
    """True when package_id() unconditionally runs self.info.requires.clear()."""
    for cls in _class_nodes(conanfile_path):
        for fn in cls.body:
            if isinstance(fn, ast.FunctionDef) and fn.name == "package_id":
                for stmt in fn.body:  # only top-level statements: not conditional
                    call = stmt.value if isinstance(stmt, ast.Expr) else None
                    if (
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "clear"
                        and ast.unparse(call.func.value) == "self.info.requires"
                    ):
                        return True
    return False


def version_change_affects_package_id(mode: str, baseline: str, new_version: str) -> bool:
    """True when switching from baseline to new_version changes the package_id under `mode`."""
    old, new = Version(baseline), Version(new_version)
    if mode == "major_mode":
        return old.major != new.major
    if mode == "semver_mode":
        if old.major != 0 or new.major != 0:
            return old.major != new.major
        return (old.major, old.minor) != (new.major, new.minor)
    if mode == "minor_mode":
        return (old.major, old.minor) != (new.major, new.minor)
    if mode == "patch_mode":
        return (old.major, old.minor, old.patch) != (new.major, new.minor, new.patch)
    # full_mode / recipe_revision_mode (and anything unknown): any new version differs
    return str(old) != str(new)
