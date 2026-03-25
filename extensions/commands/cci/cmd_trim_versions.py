import json
from collections import defaultdict
from pathlib import Path

from conan.api.conan_api import ConanAPI
from conan.api.output import Color, ConanOutput, cli_out_write
from conan.cli.command import conan_command
from conan.tools.scm import Version
from typing import Dict, List, Set
from conan.api.input import UserInput
from cmd_list import add_reference_args, resolve_profile_args
from parser.output import print_usages
from parser.analyzer import DependenciesAnalyzer
from parser.utils import invalidate_cache_entry
from conan.cli.args import add_profiles_args
import subprocess


@conan_command(group="Conan Center Index")
def trim_versions(conan_api: ConanAPI, parser, *args):
    """
    Trim old versions based on different heuristics and cross-references.
    """
    add_reference_args(parser)
    parser.add_argument("--max-versions", help="Maximum permited versions per recipe", default=10)
    parser.add_argument("--max-recipes", help="Maximum number of recipes to trim", default=1000)
    parser.add_argument(
        "--confirm",
        help="Apply changes on config.yml, conandata.yml and possibly remove not used patches",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--ignore-refs-file",
        help="Precomputed JSON of references referenced in any dependency graph which can't be removed",
        default=None,
    )
    add_profiles_args(parser)
    args = parser.parse_args(*args)
    profile_host, profile_build = resolve_profile_args(conan_api, args)

    max_versions = int(args.max_versions)
    max_recipes = int(args.max_recipes)
    ignore_refs_file = args.ignore_refs_file
    recipe_version_map: Dict[str, int] = {}

    recipes_trimmed = 0
    versions_to_ignore: Dict[str, Set[Version]] = defaultdict(set)
    yaml = get_yaml_instance()

    ui = UserInput(False)

    analyzer = (
        DependenciesAnalyzer(Path(args.recipes_path))
        .analyze(no_cache=args.no_cache)
        .evaluate(
            conan_api,
            profile_host,
            profile_build,
            args.fallback,
            no_cache=args.no_cache,
        )
    )

    def confirmation(message):
        return args.confirm or ui.request_boolean(message)

    if ignore_refs_file:
        with open(ignore_refs_file) as file:
            ignore_refs = json.load(file)
            for recipe_version in ignore_refs:
                recipe, version = recipe_version.split("/")
                versions_to_ignore[recipe].add(Version(version))

    cli_out_write("Trimming recipes", fg=Color.BRIGHT_YELLOW)
    recipes_to_trim = [args.reference] if args.reference else analyzer.dependencies.keys()

    for recipe in recipes_to_trim:
        if recipes_trimmed >= max_recipes:
            break
        cli_out_write(f"- {recipe}", fg=Color.BRIGHT_CYAN)
        versions = [
            Version(v)
            for all_versions in [recipe_dependencies.versions for recipe_dependencies in analyzer.dependencies[recipe]]
            for v in all_versions
        ]
        num_versions = len(versions)
        recipe_version_map[recipe] = num_versions

        if num_versions <= max_versions:
            cli_out_write(
                f"    Skip: versions {num_versions} <= {max_versions}",
                fg=Color.BRIGHT_GREEN,
            )
            continue

        # If there is at least a cci version we can't automate the task
        cci_versions = [version for version in versions if str(version).startswith("cci.")]
        if any(cci_versions):
            cli_out_write(
                f"    Skip: Contains cci versions: {cci_versions}",
                fg=Color.BRIGHT_YELLOW,
            )
            continue

        recipe_usages = analyzer.get_usages(recipe, only_default=args.only_default)
        print_usages(recipe_usages)

        # Clear versions
        latest_major = versions[0].major
        latest_minor = versions[0].minor or 0
        latest_patch = versions[0].patch or 0

        default_usaged_versions: Set[Version] = set()
        non_default_usaged_versions: Set[Version] = set()
        unknown_default_usaged_versions: Set[Version] = set()
        old_patches_to_remove: List[Version] = []

        def check_version_default_attr(version: Version):
            has_default = False
            if str(version) in recipe_usages[recipe]:
                for usages in recipe_usages[recipe][str(version)].values():
                    for usage in usages:
                        if usage.default == "Unknown":
                            unknown_default_usaged_versions.add(Version)
                            has_default = True
                            break
                        if usage.default:
                            default_usaged_versions.add(version)
                            has_default = True
                            break
                if not has_default:
                    non_default_usaged_versions.add(version)
            return has_default

        check_version_default_attr(versions[0])

        try:
            for version in versions[1:]:
                has_default = check_version_default_attr(version)
                if version.major != latest_major:
                    latest_major, latest_minor, latest_patch = (
                        version.major,
                        version.minor,
                        version.patch,
                    )
                    continue
                elif (version.minor or 0) != latest_minor:
                    latest_minor, latest_patch = version.minor, version.patch
                    continue
                elif (version.patch or 0) != latest_patch:
                    # Old minor
                    if not has_default and version not in versions_to_ignore[recipe]:
                        old_patches_to_remove.append(version)

        except Exception as e:
            cli_out_write(f"    Skip: exception {str(e)} -> {version}", fg=Color.BRIGHT_RED)
            continue

        total_to_remove = len(versions) - max_versions
        diff = total_to_remove - len(old_patches_to_remove)
        # To reach the max-versions, we can remove all candidates
        if diff <= 0:
            old_patches_to_remove = old_patches_to_remove[abs(diff) :]

        candidates = set(old_patches_to_remove)

        def print_candidates(versions_to_remove: Set[Version]):
            cli_out_write(
                f"    - Candidates to remove: {version_list_to_str(sorted(versions_to_remove, reverse=True))}"
            )
            cli_out_write(
                f"    - Final versions:       {version_list_to_str(sorted(set(versions) - versions_to_remove, reverse=True))}"
            )

        def trim_other_versions(diff, candidates, ignore_version_set: Set[Version] | None = None):
            new_to_remove = set(versions) - set(candidates) - versions_to_ignore[recipe]
            if ignore_version_set:
                new_to_remove -= ignore_version_set

            valid_versions_to_remove = sorted(list(new_to_remove), reverse=True)
            new_versions_to_remove = valid_versions_to_remove[-diff:]
            if not new_versions_to_remove:
                cli_out_write(
                    "    Could not find more versions to remove with this criteria",
                    fg=Color.BRIGHT_RED,
                )
                return diff
            cli_out_write(
                f"    Versions to remove added: {version_list_to_str(new_versions_to_remove)}",
                fg=Color.BRIGHT_RED,
            )
            candidates |= set(new_versions_to_remove)
            diff = total_to_remove - len(candidates)
            print_candidates(candidates)
            return diff

        cli_out_write(f"    Found {num_versions} versions")
        cli_out_write(f"    - Existing versions:    {version_list_to_str(versions)}")
        print_candidates(candidates)

        # We need to remove more versions than the preselected candidates
        if diff > 0 and confirmation("    Not enough patches to remove, do you want to select versions not in use?"):
            diff = trim_other_versions(
                diff,
                candidates,
                default_usaged_versions | non_default_usaged_versions | unknown_default_usaged_versions,
            )
            if diff > 0 and confirmation(
                f"    Still need to remove {diff} more versions, do you want to continue selecting versions used (NON DEFAULT) in CCI?"
            ):
                diff = trim_other_versions(
                    diff,
                    candidates,
                    default_usaged_versions | unknown_default_usaged_versions,
                )
                if diff > 0 and confirmation(
                    f"    Still need to remove {diff} more versions, do you want to continue selecting versions used (UNKNOWN) in CCI?"
                ):
                    diff = trim_other_versions(diff, candidates, default_usaged_versions)
                    if diff > 0 and confirmation(
                        f"    Still need to remove {diff} more versions, do you want to continue selecting versions USED (DEFAULT) in CCI?"
                    ):
                        diff = trim_other_versions(diff, candidates)
                        if diff > 0:
                            cli_out_write(
                                f"    Still need to remove {diff} more versions but there are no more candidates",
                                fg=Color.BRIGHT_RED,
                            )

        if confirmation(f"    Remove {len(candidates)} versions from {recipe}?"):
            # Take the first conanfile (does not matter which one)
            config_file_path = analyzer.dependencies[recipe][0].conanfile_path.parent.parent / "config.yml"
            trim_yaml_files(list(candidates), config_file_path, yaml)
            # Invoke linter to detect unused patches and dead code branches
            lint_recipe(Path(args.recipes_path), recipe, confirmation)
            recipes_trimmed += 1
            # As the recipe will suffer modifications, invalidate Analyzer entry for this recipe
            for conanfile in analyzer.dependencies[recipe]:
                # Invalidate all of the conanfiles -> easier
                invalidate_cache_entry(conanfile.conanfile_path)


def version_list_to_str(versions: List[Version]) -> str:
    return ", ".join(str(version) for version in versions)


def get_yaml_instance():
    # Scoped import to avoid missing dependencies
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True  # Preserve quotes in the YAML file
    yaml.indent(sequence=4, offset=2)  # Set indentation for lists and key-values
    yaml.width = 1000  # Avoid line breaks refactors when saving
    return yaml


def trim_yaml_files(versions: list, config_file: Path, yaml) -> None:
    with open(config_file, "r") as file:
        config_data = yaml.load(file)
    for version in versions:
        version = str(version)
        # Get the folder where the conandata.yml is located for the specific version
        folder = config_data["versions"][version]["folder"]
        # Delete the versions keys on config.yml
        del config_data["versions"][version]
        conandata_file = config_file.parent / folder / "conandata.yml"
        with open(conandata_file, "r") as conandata_yml:
            conandata = yaml.load(conandata_yml)
            # Delete `sources` and `patches` keys for versions in conandata.yml
            if version not in conandata["sources"]:
                ConanOutput().warning(f"Version {version} not found in conandata.yml sources but it's in config.yml")
                continue
            del conandata["sources"][version]
            if "patches" in conandata:
                if version in conandata["patches"]:
                    del conandata["patches"][version]
                # Avoid empty patches key
                if conandata["patches"] == {}:
                    del conandata["patches"]
            with open(conandata_file, "w") as conandata_yml:
                yaml.dump(conandata, conandata_yml)
    with open(config_file, "w") as file:
        yaml.dump(config_data, file)


def lint_recipe(recipes_path: Path, recipe: str, confirmation):
    subprocess.run(
        [
            "conanlint",
            "-d",
            "all",
            "-e",
            "cci-patch-file-not-used",
            "-e",
            "conan-unreachable-branch",
            "-e",
            "conan-condition-evals-to-constant",
            "check",
            f"{recipes_path}/{recipe}/**/*",
            "--format=json",
            "--output=lint.json",
            f"--relative-to={recipes_path}",
        ]
    )

    cli_out_write("    Running conanlint", fg=Color.BRIGHT_BLUE)

    with open("lint.json") as lint_file:
        lint_data = json.load(lint_file)
        if "messages" in lint_data:
            for message in lint_data["messages"]:
                cli_out_write(f"    - {message['path']}:{message['line']} -> ", endline="")
                cli_out_write(f"{message['message']}", fg=Color.BRIGHT_YELLOW)
                if "cci-patch-file-not-used" in message["symbol"]:
                    patch_file_to_remove = message["message"].split(" ")[2]
                    patch_file_to_remove = (recipes_path / message["path"]).parent / "patches" / patch_file_to_remove
                    if confirmation(f"      Remove {patch_file_to_remove} from the recipe?"):
                        patch_file_to_remove.unlink()
                        if not list(patch_file_to_remove.parent.glob("*")):
                            if confirmation(f"      Remove empty folder {patch_file_to_remove.parent}?"):
                                patch_file_to_remove.parent.rmdir()

                elif "conan-unreachable" in message["symbol"]:
                    if confirmation("      [Experimental] Remove previous dead code?"):
                        cli_out_write(
                            "      This feature is not implemented yet",
                            fg=Color.BRIGHT_RED,
                        )

                elif "conan-condition-evals-to-constant" in message["symbol"]:
                    if confirmation("      [Experimental] Remove previous condition on constant statement?"):
                        cli_out_write(
                            "      This feature is not implemented yet",
                            fg=Color.BRIGHT_RED,
                        )

    Path("lint.json").unlink(missing_ok=True)
