from parser.utils import persistent_cache_by_file_mtime
from parser.recipe_visitor import RecipeVisitor
from parser.ast_utils import link_ast
from parser.evaluator import ConditionEvaluator
from parser.recipe_dependencies import RecipeDependencies
from parser.utils import get_available_versions
import ast
from pathlib import Path
import tokenize

_MAX_REQUIREMENT_EXPR_DEPTH = 12


@persistent_cache_by_file_mtime
def extract_conan_dependencies(recipe_path: Path):
    # Pass stream into AST by reading the file using tokenize instead of plain open/read_text
    with tokenize.open(recipe_path) as f:
        recipe_source = f.read()
    tree = ast.parse(recipe_source, filename=recipe_path)
    link_ast(tree)
    visitor = RecipeVisitor(recipe_path)
    visitor.visit(tree)

    versions = get_available_versions(recipe_path)
    deps = RecipeDependencies(versions, recipe_path)
    for node, conditions in visitor.requirements:
        extract_requirement(deps, visitor, node, conditions, "requires")
    for node, conditions in visitor.tool_requirements:
        extract_requirement(deps, visitor, node, conditions, "tool_requires")
    return deps


def extract_requirement(deps: RecipeDependencies, visitor: RecipeVisitor, node, conditions, dep_type: str):
    # args[0] is the actual requirement
    # There should only be one argument, the rest are named arguments, e.g. transitive_headers=True
    arg = node.args[0]

    condition = ConditionEvaluator(visitor).parse(conditions)
    context = "requirements" if dep_type == "requires" else "build_requirements"
    _add_requirement_from_expr(deps, visitor, arg, node, condition, context, dep_type, depth=0)


def _add_requirement_from_expr(
    deps: RecipeDependencies,
    visitor: RecipeVisitor,
    expr: ast.AST,
    call_node: ast.Call,
    condition,
    context: str,
    dep_type: str,
    depth: int,
):
    if depth > _MAX_REQUIREMENT_EXPR_DEPTH:
        return

    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        dep = expr.value
        dep_name, dep_version = dep.split("/")
        deps.add(dep_name, dep_version, dep_type, condition)

    elif isinstance(expr, ast.JoinedStr):
        version_map = {}
        requirement = ""
        for value in expr.values:
            result = visitor.parse_part(call_node, value, context)
            if isinstance(result, str):
                requirement += result
            else:
                version_map = result
                requirement += "%s"

        if version_map:
            for recipe_version, requirement_version in version_map.items():
                dep_name, dep_version = (requirement % requirement_version).split("/")
                deps.add(
                    dep_name,
                    dep_version,
                    dep_type,
                    condition,
                    version=str(recipe_version),
                )
        else:
            dep_name, dep_version = requirement.split("/")
            deps.add(
                dep_name,
                dep_version,
                dep_type,
                condition,
            )

    elif isinstance(expr, ast.Name):
        assign = visitor.get_local_assignments(expr.id, call_node, context)
        if assign is None:
            return
        _add_requirement_from_expr(
            deps, visitor, assign.value, call_node, condition, context, dep_type, depth + 1
        )
