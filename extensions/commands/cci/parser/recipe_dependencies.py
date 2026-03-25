from pathlib import Path
from conan.tools.scm import Version
from conan.internal.model.profile import Profile
from collections import defaultdict
from parser.fallback import fallback_evaluate, fallback_evaluate_cci
from parser.utils import is_version_range, resolve_version_range
from parser.condition import AndCondition, Condition, UnknownCondition, VersionCondition
from typing import Dict, List
from conan.api.conan_api import ConanAPI


class Meta:
    def __init__(
        self,
        version: str,
        conditions: Condition,
        requires: bool = False,
        tool_requires: bool = False,
        default: bool | str | None = None,
        version_range: str | None = None,
    ):
        self.version = version
        self.conditions = conditions
        self.requires = requires
        self.tool_requires = tool_requires
        self.default = default
        self.version_range = version_range

    def to_dict(self):
        return {
            "version": self.version,
            "conditions": str(self.conditions),
            "requires": self.requires,
            "tool_requires": self.tool_requires,
            "default": self.default,
            "version_range": self.version_range,
        }


# {version: {dependency: Meta}}
Dependencies = Dict[str, Dict[str, List[Meta]]]
# {version: {recipe_which_uses: [Meta]}
Usages = Dict[str, Dict[str, List[Meta]]]


class RecipeDependencies:
    def __init__(self, versions, conanfile_path):
        self.deps: Dependencies = defaultdict(dict)
        self.versions = [str(version) for version in versions]
        self.conanfile_path = conanfile_path
        self.recipes_path = Path(self.conanfile_path).parent.parent.parent

    def add(
        self,
        dep_name: str,
        dep_version: str,
        dep_type: str,
        condition: Condition,
        version: Version | None = None,
    ):
        version_range = None
        if is_version_range(dep_version):
            version_range = dep_version
            dep_version = resolve_version_range(self.recipes_path, dep_name, dep_version)

        if not version:
            for v in self.versions:
                if not self.handle_tool_requires(dep_type, dep_name, dep_version, v):
                    self.deps[v].setdefault(dep_name, []).append(
                        Meta(
                            version=dep_version,
                            conditions=condition,
                            requires=dep_type == "requires",
                            tool_requires=dep_type == "tool_requires",
                            version_range=version_range,
                        )
                    )
        else:
            version = str(version)
            if not self.handle_tool_requires(dep_type, dep_name, dep_version, version):
                self.deps[version].setdefault(dep_name, []).append(
                    Meta(
                        version=dep_version,
                        conditions=condition,
                        requires=dep_type == "requires",
                        tool_requires=dep_type == "tool_requires",
                        version_range=version_range,
                    )
                )

    def handle_tool_requires(self, dep_type: str, dep_name: str, dep_version: str, version: str):
        result = False
        if dep_type == "tool_requires" and dep_name in self.deps[version]:
            for meta in self.deps[version][dep_name]:
                if meta.version == dep_version:
                    # This will also handle <host_version>
                    meta.tool_requires = True
                    result = True
        return result

    def resolve_host_version(self, dep: str):
        for version in self.versions:
            for requirement in self.deps[version].keys():
                req_name, req_version = requirement.split("/")
                if dep in req_name:
                    return req_version

    def evaluate(
        self,
        conan_api: ConanAPI,
        profile_host: Profile | None = None,
        profile_build: Profile | None = None,
        fallback: bool = False,
        no_cache: bool = False,
    ):
        for version, deps in self.deps.items():
            for dep, meta_list in deps.items():
                for meta in meta_list:
                    condition = meta.conditions
                    if isinstance(condition, UnknownCondition):
                        default = "Unknown"
                        if profile_host or profile_build:
                            fallback_deps = fallback_evaluate(
                                self.conanfile_path,
                                version,
                                profile_host,
                                profile_build,
                            )
                        elif fallback:
                            fallback_deps = fallback_evaluate_cci(
                                self.conanfile_path,
                                version,
                                conan_api,
                                no_cache=no_cache,
                            )
                        else:
                            fallback_deps = None
                        if fallback_deps is not None:
                            dependency = f"{dep}/{meta.version}"
                            default = (
                                len(fallback_deps) > 0
                                and dependency in fallback_deps
                                and fallback_deps[dependency] == meta.tool_requires
                            )
                    else:
                        default = condition.evaluate(
                            version=version,
                            profile_host=profile_host,
                            profile_build=profile_build,
                        )
                    # Avoid printing Version dependant dependencies when default is False
                    if not condition.printable:
                        continue
                    meta.default = default
