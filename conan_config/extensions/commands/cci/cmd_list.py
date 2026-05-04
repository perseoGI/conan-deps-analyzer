from pathlib import Path
from conan.api.conan_api import ConanAPI
from conan.api.output import Color, cli_out_write
from conan.cli.command import conan_command, conan_subcommand
from conan.cli.args import add_profiles_args
from conan.cli.printers import print_profiles
from parser.output import print_dependencies, print_usages, dump
from parser.analyzer import DependenciesAnalyzer
from typing import Dict, List
import json


@conan_command(group="Conan Center Index")
def list(conan_api: ConanAPI, parser, *args):
    """
    Interact with recipe dependencies, versions and usages
    """


def output_text_versions(result: dict) -> None:
    if result["count"]:
        cli_out_write("Versions count:", fg=Color.BRIGHT_YELLOW)
        for recipe_name, versions in result["versions"]:
            cli_out_write(f"- {recipe_name}:", endline=" ", fg=Color.CYAN)
            cli_out_write(len(versions), fg=Color.BRIGHT_YELLOW)
        cli_out_write(f"\nTotal average: {result['avg']:.2f}", fg=Color.BRIGHT_YELLOW)
        cli_out_write(
            f"Total std deviation: {result['std_deviation']:.2f}",
            fg=Color.BRIGHT_YELLOW,
        )
    else:
        cli_out_write("All versions:", fg=Color.BRIGHT_YELLOW)
        for recipe_name, versions in result["versions"]:
            cli_out_write(f"- {recipe_name}", fg=Color.CYAN)
            for version in versions:
                cli_out_write(f"    {recipe_name}/{version}", fg=Color.BRIGHT_YELLOW)


def output_json_versions(result: dict) -> None:
    res = {recipe: len(versions) for recipe, versions in result["versions"]} if result["count"] else result["versions"]
    cli_out_write(json.dumps(dict(res), indent=2))


@conan_subcommand(formatters={"text": output_text_versions, "json": output_json_versions})
def list_versions(conan_api: ConanAPI, parser, subparser, *args):
    """
    List the number of versions of recipes with several filters
    """
    add_reference_args(subparser)
    subparser.add_argument(
        "--min",
        help="Minimum versions a recipe should have to retrieve information",
        default=1,
    )
    subparser.add_argument(
        "--max",
        help="Maximum versions a recipe should have to retrieve information",
        default=None,
    )
    subparser.add_argument(
        "--only-referenced",
        help="Get only the versions used by other recipes",
        action="store_true",
        default=None,
    )
    subparser.add_argument("--count", help="Get only numbers", action="store_true", default=False)
    args = parser.parse_args(*args)

    min_filter = int(args.min)
    max_filter = int(args.max) if args.max else None
    recipe_version_map: Dict[str, List[str]] = {}
    versions: List[int] = []

    analyzer = DependenciesAnalyzer(Path(args.recipes_path)).analyze(no_cache=args.no_cache)
    recipe_version_map = analyzer.get_versions(
        args.reference,
        min_filter,
        max_filter,
        only_referenced=args.only_referenced,
        only_default=args.only_default,
    )
    versions = [len(versions) for _, versions in recipe_version_map.items()]
    avg = sum(versions) / len(versions)
    std_deviation = (sum((num_versions - avg) ** 2 for num_versions in versions) / len(versions)) ** 0.5

    return {
        "versions": sorted(recipe_version_map.items(), key=lambda x: len(x[1]), reverse=True),
        "count": args.count,
        "avg": avg,
        "std_deviation": std_deviation,
    }


def output_json(result: dict) -> None:
    cli_out_write(dump(result))


def output_tapaholes(result: dict) -> None:
    dependant_revisions = []
    for recipe_version in result.values():
        for recipe_revision in recipe_version.values():
            for dependant, usages in recipe_revision.items():
                for usage in usages:
                    dependant_revisions.append(f"{dependant}/{usage.version}")
    cli_out_write("\n".join(dependant_revisions))


@conan_subcommand(
    formatters={
        "text": lambda usages: print_usages(usages),
        "json": output_json,
        "tapaholes": output_tapaholes,
    }
)
def list_usages(conan_api: ConanAPI, parser, subparser, *args):
    """
    Get usages of recipes in Conan Center Index
    """
    add_reference_args(subparser)
    add_profiles_args(subparser)
    subparser.add_argument(
        "--transitive",
        "-t",
        help="Calculate transitive usages",
        action="store_true",
        default=False,
    )
    subparser.add_argument(
        "--only-version-range",
        help="List only consumers that depend on the recipe via a version range",
        action="store_true",
        default=False,
    )
    args = parser.parse_args(*args)
    profile_host, profile_build = resolve_profile_args(conan_api, args)
    return (
        DependenciesAnalyzer(Path(args.recipes_path))
        .analyze(no_cache=args.no_cache)
        .evaluate(
            conan_api,
            profile_host,
            profile_build,
            args.fallback,
            no_cache=args.no_cache,
        )
        .get_usages(
            ref=args.reference,
            only_default=args.only_default,
            transitive=args.transitive,
            only_version_range=args.only_version_range,
        )
    )


@conan_subcommand(formatters={"text": lambda deps: print_dependencies(deps), "json": output_json})
def list_dependencies(conan_api: ConanAPI, parser, subparser, *args):
    """
    List all dependencies of a recipe
    """

    add_reference_args(subparser)
    add_profiles_args(subparser)
    subparser.add_argument(
        "--only-version-range",
        help="List only dependencies declared with a version range",
        action="store_true",
        default=False,
    )
    args = parser.parse_args(*args)
    profile_host, profile_build = resolve_profile_args(conan_api, args)

    return (
        DependenciesAnalyzer(Path(args.recipes_path))
        .analyze(no_cache=args.no_cache)
        .evaluate(
            conan_api,
            profile_host,
            profile_build,
            args.fallback,
            no_cache=args.no_cache,
        )
        .get_dependencies(
            ref=args.reference,
            only_default=args.only_default,
            only_version_range=args.only_version_range,
        )
    )


def add_reference_args(subparser):
    subparser.add_argument(
        "recipes_path",
        help="Path to the whole recipes repository",
    )
    subparser.add_argument("--reference", "-r", help="Recipe reference", default=None)
    subparser.add_argument(
        "--only-default",
        help="Get only defaulty used dependencies",
        action="store_true",
        default=False,
    )
    subparser.add_argument(
        "--no-cache",
        help="Do not use cache while parsing recipes for dependencies",
        action="store_true",
        default=False,
    )
    subparser.add_argument(
        "--fallback",
        help="Fallback evaluate dependencies using CCI profiles if cannot determite default value. Will take more time",
        action="store_true",
        default=False,
    )


def resolve_profile_args(conan_api, args):
    if any(
        (
            args.profile_host,
            args.profile_build,
            args.profile,
            args.options_host,
            args.options_build,
            args.options,
            args.settings_host,
            args.settings_build,
            args.settings,
            args.conf_host,
            args.conf_build,
            args.conf,
        )
    ):
        profile_host, profile_build = conan_api.profiles.get_profiles_from_args(args)
        print_profiles(profile_host, profile_build)
    else:
        profile_host, profile_build = None, None
    return profile_host, profile_build
