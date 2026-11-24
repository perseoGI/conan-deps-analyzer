import ast
import textwrap

from parser.ast_utils import LocalAssignmentFinder, link_ast, unlink_ast


def test_link_ast_sets_parent_and_back():
    tree = ast.parse("a = 1\nb = 2")
    link_ast(tree)
    # Root is invoked with parent=None, so top-level statements keep parent=None.
    a_node, b_node = tree.body
    assert a_node.parent is None
    assert b_node.parent is None
    assert a_node.back is None
    assert b_node.back is a_node


def test_link_ast_nested_name_has_assign_parent():
    tree = ast.parse("a = 1")
    link_ast(tree)
    assign = tree.body[0]
    name = assign.targets[0]
    assert name.parent is assign


def test_local_assignment_finder_collects_names():
    tree = ast.parse(
        textwrap.dedent(
            """
            x = 1
            y: int = 2
            def f():
                z = 3
            """
        ).strip()
    )
    finder = LocalAssignmentFinder()
    finder.visit(tree)
    assert "x" in finder.local_assignments
    assert "y" in finder.local_assignments
    assert "z" in finder.local_assignments


def test_link_ast_skip_links_node_but_not_its_children():
    tree = ast.parse("def keep():\n    a = 1\ndef skip():\n    b = 2\n")
    keep, skip = tree.body
    linked = link_ast(tree, skip=lambda n: isinstance(n, ast.FunctionDef) and n.name == "skip")
    assert skip.back is keep
    assert keep.body[0].parent is keep
    assert not hasattr(skip.body[0], "parent")
    assert skip in linked and skip.body[0] not in linked


def test_unlink_ast_breaks_parent_cycles():
    tree = ast.parse("a = 1")
    linked = link_ast(tree)
    unlink_ast(linked)
    assert all(node.parent is None for node in linked)
