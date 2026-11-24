from pathlib import Path
import yaml
from conan.tools.scm import Version
from conan.errors import ConanException
from conan.api.conan_api import ConanAPI
from functools import lru_cache
import atexit
import functools
import hashlib
import os
import pickle
import tempfile

CACHE_DB_PATH = Path(__file__).parent / ".conan2_parser.pickle"

try:
    _YAML_LOADER = yaml.CSafeLoader  # libyaml bindings, ~10x faster than the pure Python loader
except AttributeError:  # pragma: no cover - depends on how PyYAML was built
    _YAML_LOADER = yaml.SafeLoader


def _yaml_load(stream):
    return yaml.load(stream, Loader=_YAML_LOADER)


class _PersistentCache:
    """
    Whole-file pickle cache: loaded once on first access and written back once at exit (only if it
    changed). Opening a dbm/shelve database per recipe dominated the run time when the cache was warm.
    Each entry keeps its result pickled, so every hit returns a fresh copy that callers may mutate.
    """

    def __init__(self, path: Path):
        self.path = path
        self._entries: dict | None = None
        self._dirty = False

    @property
    def entries(self) -> dict:
        if self._entries is None:
            self._entries = self._load()
            atexit.register(self.flush)
        return self._entries

    def _load(self) -> dict:
        try:
            with open(self.path, "rb") as f:
                data = pickle.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            # Missing, corrupted or written by an incompatible version: start from scratch
            return {}

    def get(self, key):
        return self.entries.get(key)

    def set(self, key, value):
        self.entries[key] = value
        self._dirty = True

    def delete(self, key):
        if self.entries.pop(key, None) is not None:
            self._dirty = True

    def flush(self):
        if not self._dirty or self._entries is None:
            return
        try:
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=self.path.name, suffix=".tmp")
            with os.fdopen(fd, "wb") as f:
                pickle.dump(self._entries, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, self.path)  # atomic: concurrent runs never see a half-written file
            self._dirty = False
        except OSError:
            pass


_CACHE = _PersistentCache(CACHE_DB_PATH)


def _hash_args(*args, **kwargs):
    """Helper to hash function arguments for uniqueness."""
    key_data = pickle.dumps((args, kwargs))
    return hashlib.sha256(key_data).hexdigest()


# Stack of sets collecting the YAML files read while a cached function runs (one set per nested call)
_tracked_files: list[set[Path]] = []


def _track_file(path: Path):
    for files in _tracked_files:
        files.add(Path(path))


def _mtime_or_none(path: Path):
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _files_unchanged(files: dict) -> bool:
    return all(_mtime_or_none(Path(path)) == mtime for path, mtime in files.items())


def persistent_cache_by_file_mtime(func):
    """
    Cache results on disk, keyed by the arguments. An entry is valid while neither `file_path` nor any
    YAML file read through this module during the call (the recipe's config.yml/conandata.yml and the
    config.yml of dependencies whose version ranges were resolved) has been modified.
    """

    @functools.wraps(func)
    def wrapper(file_path: Path, *args, **kwargs):
        no_cache = kwargs.pop("no_cache", True)
        mtime = file_path.stat().st_mtime
        args_without_conan_api = [arg for arg in args if not isinstance(arg, ConanAPI)]
        call_hash = _hash_args(file_path, *args_without_conan_api)

        if not no_cache:
            cached_entry = _CACHE.get(call_hash)
            if (
                cached_entry
                and cached_entry["mtime"] == mtime
                and "files" in cached_entry  # entries from older versions don't track files
                and _files_unchanged(cached_entry["files"])
            ):
                result = pickle.loads(cached_entry["result"])
                # Let an enclosing cached call know which files this result depended on
                for path in cached_entry["files"]:
                    _track_file(Path(path))
                return result
        _tracked_files.append(set())
        try:
            result = func(file_path, *args, **kwargs)
        finally:
            read_files = _tracked_files.pop()
        for path in read_files:
            _track_file(path)
        # Always store result in the cache
        _CACHE.set(
            call_hash,
            {
                "mtime": mtime,
                "result": pickle.dumps(result),
                "files": {str(path): _mtime_or_none(path) for path in read_files},
            },
        )
        return result

    return wrapper


def flush_cache():
    """Persist pending cache changes now (also done automatically at interpreter exit)."""
    _CACHE.flush()


def invalidate_cache_entry(file_path: Path):
    """Invalidate the cache entry for a specific file path."""
    _CACHE.delete(_hash_args(file_path))


def get_available_versions(recipe_path: Path):
    config_path = recipe_path.parent.parent / "config.yml"
    folder = recipe_path.parent.name
    return get_available_versions_from_config(config_path, folder)


def get_available_versions_from_config(config_path: Path, folder: str | None = None):
    _track_file(config_path)
    return _get_available_versions_from_config(config_path, folder)


@lru_cache(maxsize=None)
def _get_available_versions_from_config(config_path: Path, folder: str | None = None):
    # Error control
    with open(config_path, "r") as f:
        try:
            config = _yaml_load(f)
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


def get_conandata(recipe_path: Path):
    _track_file(recipe_path.parent / "conandata.yml")
    return _get_conandata(recipe_path)


@lru_cache(maxsize=None)
def _get_conandata(recipe_path: Path):
    conandata_path = recipe_path.parent / "conandata.yml"
    with open(conandata_path, "r") as f:
        try:
            return _yaml_load(f)
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


def missing_binaries_breaking_minor_line(resolved_dep: str | None, new_version: str, latest_published: str) -> bool:
    """
    True when the hypothetical new_version crosses a different (major, minor) line than the
    baseline resolution of the dependency (current resolved version, or latest published if
    the range does not resolve yet).
    """
    baseline = resolved_dep if resolved_dep is not None else latest_published
    if not baseline:
        return True
    try:
        v_new = Version(new_version)
        v_base = Version(baseline)
        return (v_new.major, v_new.minor) != (v_base.major, v_base.minor)
    except Exception:
        return True


def new_version_would_be_selected(version_range: str | None, resolved_dep: str | None, new_version: str) -> bool:
    """
    True when a consumer requiring `version_range` (e.g. "[>=1.5 <3]") would resolve to new_version
    once published: it must satisfy the range and be newer than the currently resolved version.
    """
    if not version_range:
        return False
    try:
        v_new = Version(new_version)
        if not v_new.in_range(version_range[1:-1]):
            return False
        return resolved_dep is None or v_new > Version(resolved_dep)
    except Exception:
        return True
