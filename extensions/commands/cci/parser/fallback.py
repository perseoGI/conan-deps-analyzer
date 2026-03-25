from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from conan.api.model import RecipeReference
from conan.internal.model.options import Options
from conan.internal.graph.graph import CONTEXT_HOST
from conan.internal.loader import ConanFileLoader
from conan.internal.graph.profile_node_definer import initialize_conanfile_profile
from conan.internal.methods import run_configure_method
from conan.internal.model.profile import Profile
from parser.utils import (
    is_version_range,
    persistent_cache_by_file_mtime,
    resolve_version_range,
)
from conan.api.conan_api import ConanAPI
from typing import Dict, Iterable
from collections import defaultdict


@lru_cache(maxsize=32)
def fallback_evaluate(recipe_path: Path, version: str, profile_host: Profile, profile_build: Profile):
    name = recipe_path.parent.parent.name
    ref = RecipeReference(name, version, "", "")
    if profile_host or profile_build:
        if not (conanfile := load_conanfile(recipe_path, ref)):
            return None
        return retrive_deps(recipe_path, profile_host, profile_build, conanfile, ref)


@persistent_cache_by_file_mtime
def fallback_evaluate_cci(recipe_path: Path, version: str, conan_api: ConanAPI):
    profiles_path = Path(__file__).parent.parent.parent.parent.parent / "profiles"
    dependencies = []
    for profile_host, profile_build in CCI_PROFILES:
        profile_args = SimpleNamespace(
            profile_host=[f"{profiles_path}/{profile_host}"],
            profile_build=[f"{profiles_path}/{profile_build}"],
            settings_host=[],
            options_host=[],
            conf_host=[],
            settings_build=[],
            options_build=[],
            conf_build=[],
        )
        profile_host, profile_build = conan_api.profiles.get_profiles_from_args(profile_args)
        if not (deps := fallback_evaluate(recipe_path, version, profile_host, profile_build)):
            return None
        dependencies.append(deps)
    return merge_dicts(dependencies)


def load_conanfile(recipe_path: Path, ref: RecipeReference):
    loader = ConanFileLoader()
    try:
        conanfile = loader.load_conanfile(str(recipe_path.resolve()), ref)
    except Exception:
        return None
    return conanfile


def retrive_deps(recipe_path, profile_host, profile_build, conanfile, ref):
    initialize_conanfile_profile(conanfile, profile_build, profile_host, CONTEXT_HOST, False, ref)
    run_configure_method(conanfile, Options(), Options(), ref)

    dependencies = {}
    recipes_path = recipe_path.parent.parent.parent
    for dep in conanfile.requires.serialize():
        dep_name, dep_version = dep["ref"].split("/")
        if is_version_range(dep_version):
            dep_version = resolve_version_range(recipes_path, dep_name, dep_version)
        dependencies[f"{dep_name}/{dep_version}"] = dep["build"]
    return dependencies


def merge_dicts(dicts: Iterable[Dict[str, bool]]) -> Dict[str, bool]:
    merged = defaultdict(bool)
    for d in dicts:
        for k, v in d.items():
            merged[k] = merged[k] or v
    return dict(merged)


CCI_PROFILES = [
    ("Linux-gcc11-x86_64-Release", "Linux-gcc11-x86_64-Release"),
    ("Macos-appleclang13-armv8-Release", "Macos-appleclang13-armv8-Release"),
    ("Macos-appleclang13-x86_64-Release", "Macos-appleclang13-armv8-Release"),
    ("Windows-msvc192-x86_64-Release", "Windows-msvc192-x86_64-Release"),
    ("Windows-msvc193-x86_64-Release", "Windows-msvc193-x86_64-Release"),
]
