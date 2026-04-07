import ast
from collections import defaultdict
import operator

OPERATOR_MAP = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


class LocalAssignmentFinder(ast.NodeVisitor):
    def __init__(self):
        self.local_assignments = defaultdict(list)

    def visit_Assign(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id
            self.local_assignments[var_name].append(node)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            self.local_assignments[var_name].append(node)
        self.generic_visit(node)


def link_ast(node, parent=None):
    """
    Recursively annotate each AST node with `.parent` and `.back` (previous sibling) attributes.
    """
    prev = None
    for child in ast.iter_child_nodes(node):
        child.parent = parent
        if prev:
            child.back = prev
        else:
            child.back = None
        link_ast(child, parent=child)
        prev = child
