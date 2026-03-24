from collections import defaultdict
from pathlib import Path
from parser.recipe_dependencies import RecipeDependencies, Dependencies, Meta, Usages
from parser.utils import is_version_range, version_range_intersects
from parser.dependency_extractor import extract_conan_dependencies
from conan.internal.model.profile import Profile
from conan.errors import ConanException
from parser.condition import NoCondition
from typing import Dict, List
from conan.tools.scm import Version
from conan.api.conan_api import ConanAPI


class DependenciesAnalyzer:
    def __init__(self, path: Path):
        self.recipe_paths = self._get_recipe_paths(path)
        self.dependencies: Dict[str, List[RecipeDependencies]] = {}
        self.with_profiles = False

    def analyze(self, no_cache: bool):
        for conanfile_path in self.recipe_paths:
            recipe_name = conanfile_path.parent.parent.name
            self.dependencies.setdefault(recipe_name, []).append(
                extract_conan_dependencies(conanfile_path, no_cache=no_cache)
            )
        return self

    def evaluate(
        self,
        conan_api: ConanAPI,
        profile_host: Profile | None = None,
        profile_build: Profile | None = None,
        fallback: bool = False,
        no_cache: bool = False,
    ):
        """
        Evaluate dependencies and usages based on the provided profiles.

        :param profiles: List of profiles to evaluate against.
        """

        for recipe_dependecies in self.dependencies.values():
            for dependencies in recipe_dependecies:
                dependencies.evaluate(conan_api, profile_host, profile_build, fallback, no_cache)
        self.with_profiles = profile_host is not None or profile_build is not None
        return self

    def get_dependencies(self, ref: str | None = None, only_default: bool = False) -> Dict[str, Dependencies]:
        dependencies = {}
        if ref:
            recipe_name, version = ref.split("/") if "/" in ref else (ref, None)
            if recipe_name not in self.dependencies:
                raise ConanException(f"Recipe {recipe_name} not found in dependencies.")
            dependencies[recipe_name] = self._get_dependencies(recipe_name, version, only_default)
        else:
            for recipe_name in self.dependencies.keys():
                dependencies[recipe_name] = self._get_dependencies(recipe_name, None, only_default)
        return dependencies

    def _get_dependencies(self, recipe_name, version_filter: str | None, only_default: bool) -> Dependencies:
        result: Dependencies = defaultdict(dict)
        version_range = is_version_range(version_filter) if version_filter else False
        for recipe_dependencies in self.dependencies[recipe_name]:
            for version, dependencies in recipe_dependencies.deps.items():
                if (
                    ((version_range and version_filter) and Version(version).in_range(version_filter[1:-1]))
                    or (version_filter and version == version_filter)
                    or not version_filter
                ):
                    for dep, meta_list in dependencies.items():
                        for meta in meta_list:
                            if not only_default or meta.default:
                                result[version].setdefault(dep, []).append(
                                    Meta(
                                        version=meta.version,
                                        conditions=meta.conditions if not only_default else NoCondition(),
                                        requires=meta.requires,
                                        tool_requires=meta.tool_requires,
                                        default=meta.default,
                                        version_range=meta.version_range,
                                    )
                                )
        return result

    def get_usages(
        self, ref: str | None = None, only_default: bool = False, transitive: bool = False
    ) -> Dict[str, Usages]:
        result = {}
        if ref:
            recipe_name, version = ref.split("/") if "/" in ref else (ref, None)
            if recipe_name not in self.dependencies:
                raise ConanException(f"Recipe {recipe_name} not found in dependencies.")
            result[recipe_name] = self._get_usages(recipe_name, version, only_default)
            if transitive:
                to_process = self._add_transitives_to_process(result[recipe_name])
                result.update(self._get_usages_transitive(only_default, to_process))
        else:
            if transitive:
                raise ConanException("Transitive usages require a specific recipe reference.")
            for recipe_name in self.dependencies.keys():
                result[recipe_name] = self._get_usages(recipe_name, None, only_default)
        return result

    def _get_usages_transitive(self, only_default: bool, to_process: set[tuple[str, str]]) -> Dict[str, Usages]:
        result = {}
        while to_process:
            recipe_name, version = to_process.pop()
            usages = self._get_usages(recipe_name, version, only_default)
            if recipe_name not in result:
                result[recipe_name] = usages
            else:
                result[recipe_name].update(usages)
            to_process.update(self._add_transitives_to_process(usages))
        return result

    def _add_transitives_to_process(self, usages):
        to_process = set()
        for recipes_per_version in usages.values():
            for recipe_name, recipe_meta_list in recipes_per_version.items():
                for recipe_meta in recipe_meta_list:
                    to_process.add((recipe_name, recipe_meta.version))
        return to_process

    def _get_usages(self, recipe_name, version_filter: str | None, only_default: bool) -> Usages:
        result: Usages = defaultdict(dict)
        version_range = is_version_range(version_filter) if version_filter else False

        for recipe, dependency_list in self.dependencies.items():
            if recipe == recipe_name:
                continue
            for deps in dependency_list:
                for version, dependencies in deps.deps.items():
                    for dep, meta_list in dependencies.items():
                        for meta in meta_list:
                            if dep == recipe_name:
                                if version_range:
                                    if meta.version_range:
                                        add_usage = version_range_intersects(version_filter, meta.version_range)
                                    else:
                                        add_usage = Version(meta.version).in_range(version_filter[1:-1])
                                elif version_filter:
                                    add_usage = version_filter == meta.version
                                else:
                                    add_usage = True

                                if add_usage:
                                    default_usage = meta.default
                                    if not only_default or default_usage:
                                        # TODO
                                        if meta.version not in result:
                                            result[meta.version] = defaultdict(list)
                                        result[meta.version][recipe].append(
                                            Meta(
                                                version=version,
                                                conditions=NoCondition() if only_default else meta.conditions,
                                                default=default_usage,
                                                version_range=meta.version_range,
                                            )
                                        )
        return result

    def get_versions(
        self,
        ref: str | None = None,
        min_filter: int = 0,
        max_filter: int | None = None,
        only_referenced: bool = False,
        only_default: bool = False,
    ) -> Dict[str, List[str]]:
        recipe_version_map: Dict[str, List[str]] = {}

        if only_referenced:
            usages = self.get_usages(ref, only_default=only_default)
            for recipe_name, usages_per_version in usages.items():
                recipe_versions = list(usages_per_version.keys())
                num_versions = len(recipe_versions)
                if num_versions >= min_filter and (not max_filter or num_versions <= max_filter):
                    recipe_version_map[recipe_name] = sorted([Version(v) for v in recipe_versions], reverse=True)
            return recipe_version_map

        if ref:
            if ref not in self.dependencies:
                raise ConanException(f"Recipe {ref} not found in dependencies.")
            recipe_version_map[ref] = [
                v
                for all_versions in [recipe_dependencies.versions for recipe_dependencies in self.dependencies[ref]]
                for v in all_versions
            ]
        else:
            for recipe_name, dependency_list in self.dependencies.items():
                for deps_per_version in dependency_list:
                    recipe_versions = deps_per_version.versions
                    num_versions = len(recipe_versions)
                    if num_versions >= min_filter and (not max_filter or num_versions <= max_filter):
                        recipe_version_map[recipe_name] = recipe_versions
        return recipe_version_map

    def _get_recipe_paths(self, path: Path):
        conanfiles = []
        if path.is_file() and path.name == "conanfile.py":
            conanfiles.append(path)
        for conanfile in path.rglob("conanfile.py"):
            # Avoid test_packages
            if not (conanfile.parent / "conandata.yml").exists():
                continue
            conanfiles.append(conanfile)
        return conanfiles


if __name__ == "__main__":
    path = Path(Path.cwd() / "tests/assets/cci_repo/recipes/foo/all")
    analyzer = DependenciesAnalyzer(path).analyze(no_cache=True).evaluate().get_dependencies()
