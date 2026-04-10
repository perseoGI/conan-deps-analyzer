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


def flatten_add_operands(expr: ast.AST) -> list[ast.AST]:
    """Left-flatten a + b + c -> [a, b, c]."""
    if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        return flatten_add_operands(expr.left) + flatten_add_operands(expr.right)
    return [expr]


def _resolve_joinedstr_parts(
    visitor: RecipeVisitor, values, call_node: ast.Call, context: str
) -> tuple[str, dict]:
    version_map: dict = {}
    requirement = ""
    for value in values:
        result = visitor.parse_part(call_node, value, context)
        if isinstance(result, str):
            requirement += result
        else:
            version_map = result
            requirement += "%s"
    return requirement, version_map


def _add_from_resolved_requirement(
    deps: RecipeDependencies,
    requirement: str,
    version_map: dict,
    dep_type: str,
    condition,
):
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
        deps.add(dep_name, dep_version, dep_type, condition)


def _fold_concat_operand_into(
    visitor: RecipeVisitor,
    operand: ast.AST,
    call_node: ast.Call,
    context: str,
    acc: dict,
    depth: int,
) -> bool:
    """
    Append one concatenation operand into acc {"requirement": str, "version_map": dict}.
    Returns False if the operand cannot be resolved (abort whole BinOp / concat).
    """
    if depth > _MAX_REQUIREMENT_EXPR_DEPTH:
        return False

    if isinstance(operand, ast.Constant) and isinstance(operand.value, str):
        acc["requirement"] += operand.value
        return True

    if isinstance(operand, ast.Name):
        assign = visitor.get_local_assignments(operand.id, call_node, context)
        if assign is None:
            return False
        return _fold_concat_operand_into(visitor, assign.value, call_node, context, acc, depth + 1)

    if isinstance(operand, ast.JoinedStr):
        requirement, version_map = _resolve_joinedstr_parts(visitor, operand.values, call_node, context)
        if version_map:
            acc["version_map"] = version_map
        acc["requirement"] += requirement
        return True

    if isinstance(operand, ast.BinOp) and isinstance(operand.op, ast.Add):
        for part in flatten_add_operands(operand):
            if not _fold_concat_operand_into(visitor, part, call_node, context, acc, depth + 1):
                return False
        return True

    result = visitor.parse_part(call_node, operand, context)
    if result == "*":
        return False
    if isinstance(result, str):
        acc["requirement"] += result
        return True
    if isinstance(result, dict):
        acc["version_map"] = result
        acc["requirement"] += "%s"
        return True
    return False


def _add_requirement_from_binop_add(
    deps: RecipeDependencies,
    visitor: RecipeVisitor,
    binop: ast.BinOp,
    call_node: ast.Call,
    condition,
    context: str,
    dep_type: str,
    depth: int,
):
    if depth > _MAX_REQUIREMENT_EXPR_DEPTH:
        return
    acc = {"requirement": "", "version_map": {}}
    for part in flatten_add_operands(binop):
        if not _fold_concat_operand_into(visitor, part, call_node, context, acc, depth + 1):
            return
    _add_from_resolved_requirement(
        deps, acc["requirement"], acc["version_map"], dep_type, condition
    )


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
        _add_from_resolved_requirement(deps, expr.value, {}, dep_type, condition)

    elif isinstance(expr, ast.JoinedStr):
        requirement, version_map = _resolve_joinedstr_parts(visitor, expr.values, call_node, context)
        _add_from_resolved_requirement(deps, requirement, version_map, dep_type, condition)

    elif isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
        _add_requirement_from_binop_add(
            deps, visitor, expr, call_node, condition, context, dep_type, depth
        )

    elif isinstance(expr, ast.Name):
        assign = visitor.get_local_assignments(expr.id, call_node, context)
        if assign is None:
            return
        _add_requirement_from_expr(
            deps, visitor, assign.value, call_node, condition, context, dep_type, depth + 1
        )
