import json
from parser.recipe_dependencies import Dependencies, Meta, Usages
from conan.api.output import cli_out_write, Color
from parser.condition import NoCondition
from typing import Dict, List


def print_usages(usages: dict[str, Usages]):
    for recipe_name, usagers in usages.items():
        cli_out_write(f"Usages of {recipe_name}", fg=Color.BRIGHT_YELLOW)
        for version, recipes_per_version in usagers.items():
            cli_out_write(f"  {version}", fg=Color.BRIGHT_MAGENTA)
            for recipe_name, uses in recipes_per_version.items():
                for detail in uses:
                    print_meta(recipe_name, detail)


def print_dependencies(dependencies: Dict[str, Dependencies]):
    for recipe_name, deps in dependencies.items():
        cli_out_write(f"Dependencies of {recipe_name}", fg=Color.BRIGHT_YELLOW)
        for version, deps in deps.items():
            print_version(version, deps)


def print_version(version, deps: Dict[str, List[Meta]]):
    cli_out_write(f"  {version}", fg=Color.BRIGHT_MAGENTA)
    requires = {
        dep: [meta for meta in meta_list if meta.requires and meta.default is not None]
        for dep, meta_list in deps.items()
    }
    tool_requires = {
        dep: [meta for meta in meta_list if meta.tool_requires and meta.default is not None]
        for dep, meta_list in deps.items()
    }
    if any(requires.values()):
        print_requires("requires", requires)
    if any(tool_requires.values()):
        print_requires("tool_requires", tool_requires)


def print_requires(kind, deps: Dict[str, List[Meta]]):
    cli_out_write(f"    {kind}:", fg=Color.BRIGHT_CYAN)
    for dep, meta_list in deps.items():
        for meta in meta_list:
            print_meta(dep, meta)


def print_meta(dep: str, meta: Meta):
    conditions = meta.conditions
    dep_version = meta.version
    cli_out_write(f"    - {dep}/{dep_version}", fg=Color.BRIGHT_GREEN)
    if not isinstance(conditions, NoCondition):
        cli_out_write("        condition: ", fg=Color.BRIGHT_BLUE, endline="")
        cli_out_write(f"{conditions}")
        cli_out_write("        default: ", fg=Color.BRIGHT_BLUE, endline="")
        cli_out_write(f"{meta.default}")
    if meta.version_range:
        cli_out_write("        version range: ", fg=Color.BRIGHT_BLUE, endline="")
        cli_out_write(f"{meta.version_range}")


def dump(deps: Dict[str, Dependencies]):
    return json.dumps(deps, indent=2, cls=ConditionEncoder)


class ConditionEncoder(json.JSONEncoder):
    def default(self, o):
        return o.to_dict()
