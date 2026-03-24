from pathlib import Path
import yaml
from conan.tools.scm import Version
from conan.errors import ConanException
from conan.api.conan_api import ConanAPI
from functools import lru_cache
import shelve
import functools
import hashlib
import pickle

CACHE_DB_PATH = Path(__file__).parent / ".conan2_parser"


def _hash_args(*args, **kwargs):
    """Helper to hash function arguments for uniqueness."""
    key_data = pickle.dumps((args, kwargs))
    return hashlib.sha256(key_data).hexdigest()


def persistent_cache_by_file_mtime(func):
    @functools.wraps(func)
    def wrapper(file_path: Path, *args, **kwargs):
        no_cache = kwargs.pop("no_cache", True)
        mtime = file_path.stat().st_mtime
        args_without_conan_api = [arg for arg in args if not isinstance(arg, ConanAPI)]
        call_hash = _hash_args(file_path, *args_without_conan_api)

        with shelve.open(CACHE_DB_PATH) as db:
            if not no_cache:
                cached_entry = db.get(call_hash)
                if cached_entry and cached_entry["mtime"] == mtime:
                    return pickle.loads(cached_entry["result"])
            result = func(file_path, *args, **kwargs)
            # Always store result in the cache
            db[call_hash] = {
                "mtime": mtime,
                "result": pickle.dumps(result),
            }
            return result

    return wrapper

def invalidate_cache_entry(file_path: Path):
    """Invalidate the cache entry for a specific file path."""
    call_hash = _hash_args(file_path)
    with shelve.open(CACHE_DB_PATH) as db:
        if call_hash in db:
            del db[call_hash]


def get_available_versions(recipe_path: Path):
    config_path = recipe_path.parent.parent / "config.yml"
    folder = recipe_path.parent.name
    return get_available_versions_from_config(config_path, folder)


@lru_cache(maxsize=32)
def get_available_versions_from_config(config_path: Path, folder: str | None = None):
    # Error control
    with open(config_path, "r") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConanException(f"Error parsing YAML file {config_path}: {e}")
    if not config or "versions" not in config or not isinstance(config["versions"], dict):
        return []
    return sorted(
        [
            Version(version)
            for version, content in config["versions"].items()
            if not folder or content["folder"] == folder
        ],
        reverse=True,
    )


@lru_cache(maxsize=32)
def get_conandata(recipe_path: Path):
    conandata_path = recipe_path.parent / "conandata.yml"
    with open(conandata_path, "r") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConanException(f"Error parsing YAML file {conandata_path}: {e}")


def is_version_range(version: Version):
    return version[0] == "[" and version[-1] == "]"


def resolve_version_range(recipes_path: Path, dep_name: str, dep_version_range: str):
    dependency_recipe_path = recipes_path / dep_name / "config.yml"
    versions = get_available_versions_from_config(dependency_recipe_path)
    dep_version_range = dep_version_range[1:-1]  # Remove brackets
    for version in versions:
        if version.in_range(dep_version_range):
            return str(version)
    return None

def version_range_intersects(version_range_filter: str, version_range: str) -> bool:
    from conan.internal.model.version_range import VersionRange
    return VersionRange(version_range_filter[1:-1]).intersection(VersionRange(version_range[1:-1])) is not None

