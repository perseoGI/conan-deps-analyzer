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
    Annotate each AST node with `.parent` and `.back` (previous sibling) attributes.
    Children of the root get `parent` (None by default); deeper nodes get their real parent.
    Iterative to avoid Python recursion overhead on ~1M nodes when indexing a whole repository.
    """
    AST = ast.AST
    stack = [(node, parent)]
    while stack:
        current, current_parent = stack.pop()
        prev = None
        for field in current._fields:
            value = getattr(current, field, None)
            if isinstance(value, AST):
                children = (value,)
            elif isinstance(value, list):
                children = value
            else:
                continue
            for child in children:
                if not isinstance(child, AST):
                    continue
                child.parent = current_parent
                child.back = prev
                stack.append((child, child))
                prev = child
