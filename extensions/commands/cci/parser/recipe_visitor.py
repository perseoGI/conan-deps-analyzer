import ast
from pathlib import Path
from typing import List
from parser.utils import get_available_versions, get_conandata
from parser.ast_utils import LocalAssignmentFinder, OPERATOR_MAP


class RecipeVisitor(ast.NodeVisitor):
    def __init__(self, conanfile_path: Path):
        self.current_method = None
        self.conanfile_path = conanfile_path
        self.versions = get_available_versions(self.conanfile_path)
        self.local_assignments = {}
        self.properties = {}
        self.attributes = {}
        self.default_options = {}
        self.options = {}
        self.requirements = []
        self.tool_requirements = []

    # Get all atributes of the class
    def visit_Assign(self, node):
        if len(node.targets) == 1 and self.current_method is None:
            if isinstance(node.targets[0], ast.Name):
                var_name = node.targets[0].id
                self.attributes[var_name] = node
                if var_name == "default_options":
                    self.default_options = self.ast_dict_to_dict(self.attributes["default_options"].value)
                    # Special case: CCI will compile both shared and static versions so any conditional dep under shared flag will be always True
                    # TODO: this will now work when negating
                    if "shared" in self.default_options:
                        self.default_options["shared"] = True
            # Handle special case: default_options["option_name"] = <value>
            elif (
                isinstance(node.targets[0], ast.Subscript)
                and isinstance(node.targets[0].value, ast.Name)
                and node.targets[0].value.id == "default_options"
                and isinstance(node.targets[0].slice, ast.Constant)
                and isinstance(node.value, ast.Constant)
            ):
                option_name = node.targets[0].slice.value
                self.default_options[option_name] = node.value.value

        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.current_method = node.name
        self.visit_property(node)
        if self.current_method in ("requirements", "build_requirements"):
            self.local_assignments[self.current_method] = self.find_local_assignments(node)
        self.generic_visit(node)
        self.current_method = None

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Attribute):
            return
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "self":
            return

        conditions = self.get_enclosing_conditions(node)

        if self.current_method == "requirements" and node.func.attr == "requires":
            self.requirements.append((node, conditions))
        elif self.current_method == "build_requirements" and node.func.attr == "tool_requires":
            self.tool_requirements.append((node, conditions))

        self.generic_visit(node)

    def visit_property(self, node):
        if any(isinstance(dec, ast.Name) and dec.id == "property" for dec in node.decorator_list):
            # Look for the return statement in the body
            for stmt in node.body:
                if isinstance(stmt, ast.Return):
                    self.properties[node.name] = stmt  # store only the expression being returned
                    break

    def get_enclosing_conditions(self, node):
        """Traverse up the AST to find enclosing if/elif/else conditions."""
        conditions = []
        current = getattr(node, "parent", None)

        while current:
            if isinstance(current, ast.If):
                # Determine if 'node' is in the body or orelse of the 'if'
                child = node
                while getattr(child, "parent", None) is not current:
                    child = child.parent

                # If in 'body', condition applies directly
                if child in current.body:
                    conditions.append(current.test)
                # If in 'orelse', the negated condition applies
                elif child in current.orelse:
                    negated = ast.UnaryOp(op=ast.Not(), operand=current.test)
                    conditions.append(negated)

            node = current
            current = getattr(current, "parent", None)

        return list(reversed(conditions))

    def find_local_assignments(self, func_node: ast.FunctionDef):
        finder = LocalAssignmentFinder()
        finder.visit(func_node)
        return finder.local_assignments

    def get_local_assignments(self, var_name: str, target_node, context: str):
        results = self.local_assignments[context].get(var_name)
        result = self.walk_back_to(results, target_node)
        return result

    def walk_back_to(self, nodes: List[ast.AST], start_node: ast.AST) -> ast.AST | None:
        """
        Given a list of target nodes and a starting node, walk backwards (up and siblings)
        to find the closest matching node from the list.
        """
        node = start_node
        while node:
            if node in nodes:
                return node
            if hasattr(node, "back") and node.back:
                node = node.back
            else:
                node = getattr(node, "parent", None)
        return None

    def parse_part(self, node, value, context: str):
        if isinstance(value, ast.Constant):
            return value.value
        elif isinstance(value, ast.FormattedValue):
            # Try to resolve the variable
            result = self.parse_part(node, value.value, context)
            return result
        elif isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name) and value.value.id == "self":
            attr_name = value.attr
            # Case: self.requires(f"pkg/{self.version}")
            if attr_name == "version":
                versions = get_available_versions(self.conanfile_path)
                return {str(version): str(version) for version in versions}
            elif property := self.properties.get(attr_name):
                return self.parse_part(node, property.value, context)
            elif property := self.attributes.get(attr_name):
                return self.parse_part(node, property.value, context)
            else:
                raise Exception(f"Unknown property {attr_name} in {self.conanfile_path}")

        # Case: self.requires(f"pkg/{pkg_version_mapping}")
        elif isinstance(value, ast.Name):
            result = self.get_local_assignments(value.id, node, context)
            if self.is_conandata_access(result.value):
                return self.handle_conandata_access(result.value.value.slice.value)
            elif isinstance(result.value, ast.IfExp):
                condition = result.value.test
                if self.is_version_comparison(condition):
                    return self.handle_version_comparison(condition, result.value)
                elif isinstance(condition, ast.Name):
                    local = self.get_local_assignments(condition.id, node, context)
                    if isinstance(local.value, ast.Name):
                        raise Exception("Loop todo")
                    elif self.is_version_comparison(local.value):
                        return self.handle_version_comparison(local.value, result.value)
                else:
                    raise Exception("Unknown assignment second", value.id)
            else:
                raise Exception("Unknown assignment", value.id)

        # Case: self.requires(f"pkg/{self.conan_data['pkg_mapping'][self.version]}")
        elif self.is_conandata_access(value):
            return self.handle_conandata_access(value.value.slice.value)
        # Case: self.requires(f"pkg/{self.conan_data.get('scip_mapping')[self.version]}")
        elif (
            isinstance(value, ast.Subscript)
            and isinstance(value.value, ast.Call)
            and isinstance(value.value.func, ast.Attribute)
            and isinstance(value.value.func.value, ast.Attribute)
            and isinstance(value.value.func.value.value, ast.Name)
            and value.value.func.value.value.id == "self"
            and value.value.func.attr == "get"
            and value.value.func.value.attr == "conan_data"
        ):
            option_name = value.value.args[0].value if isinstance(value.value.args[0], ast.Constant) else None
            return self.handle_conandata_access(option_name)

        # Case: self.requires(f"pkg/{version_map.get(version)}")
        elif (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Attribute)
            and isinstance(value.func.value, ast.Name)
            and value.func.attr == "get"
            and value.func.value.id in self.local_assignments[context]
        ):
            var_name = value.func.value.id
            property = self.get_local_assignments(var_name, node, context)
            if isinstance(property.value, ast.Dict):
                # TODO determine that .get(<variable>) is version or self.version or other thing
                has_default = len(value.args) > 1
                dictionary = self.ast_dict_to_dict(property.value)
                return self.handle_resolve_versions(dictionary, has_default)
            else:
                raise Exception(
                    f"Unknown format {value} not dict get",
                    type(value),
                )

        # Case: self.requires(f"pkg/{self._pkg_version[self.version]}")
        elif (
            isinstance(value, ast.Subscript)
            and isinstance(value.value, ast.Attribute)
            and isinstance(value.value.value, ast.Name)
            and value.value.value.id == "self"
        ):
            property = self.properties.get(value.value.attr)
            if isinstance(property.value, ast.Dict):
                return self.handle_dict_versions(value, property)
            else:
                raise Exception(
                    f"Unknown format {value} not dict",
                    type(value),
                )
        else:
            # Special case when parser cannot resolve the value: general value
            return "*"

    def is_conandata_access(self, value):
        return (
            isinstance(value, ast.Subscript)
            and isinstance(value.value, ast.Subscript)
            and isinstance(value.value.value, ast.Attribute)
            and isinstance(value.value.value.value, ast.Name)
            and value.value.value.value.id == "self"
            and value.value.value.attr == "conan_data"
            and isinstance(value.value.slice, ast.Constant)
            and isinstance(value.slice, ast.Attribute)
            and isinstance(value.slice.value, ast.Name)
            and value.slice.value.id == "self"
            and value.slice.attr == "version"
        )

    def handle_conandata_access(self, key):
        conandata = get_conandata(self.conanfile_path)
        if key in conandata:
            return self.handle_resolve_versions(conandata[key])
        raise Exception("TODO")

    def handle_resolve_versions(self, map, has_default=False):
        versions = get_available_versions(self.conanfile_path)
        res = {}
        for version in versions:
            map_version = map.get(str(version), str(version) if has_default else "*")
            res[version] = map_version
        return res

    def handle_dict_versions(self, value, property):
        if (
            isinstance(value.slice, ast.Attribute)
            and isinstance(value.slice.value, ast.Name)
            and value.slice.value.id == "self"
            and value.slice.attr == "version"
        ):
            dictionary = self.ast_dict_to_dict(property.value)
            return self.handle_resolve_versions(dictionary)
            # else: handle variables like `version`

    def is_version_comparison(self, condition):
        return (
            isinstance(condition, ast.Compare)
            and (
                # Case: Version(self.version) <op> "version"
                (
                    isinstance(condition.left, ast.Call)
                    and isinstance(condition.left.func, ast.Name)
                    and condition.left.func.id == "Version"
                    and isinstance(condition.left.args[0], ast.Attribute)
                    and condition.left.args[0].attr == "version"
                )
                # Case: self.version <op> "version"
                or (
                    isinstance(condition.left, ast.Attribute)
                    and isinstance(condition.left.value, ast.Name)
                    and condition.left.value.id == "self"
                    and condition.left.attr == "version"
                )
            )
            and isinstance(condition.comparators[0], ast.Constant)
        )

    def handle_version_comparison(self, condition, result=None, if_true=True, if_false=False):
        op_func = OPERATOR_MAP.get(type(condition.ops[0]))
        version_str = condition.comparators[0].value
        if_true = result.body.value if result else if_true
        if_false = result.orelse.value if result else if_false
        res = {}
        for v in self.versions:
            version = if_true if op_func(v, version_str) else if_false
            res[v] = version
        return res

    def ast_dict_to_dict(self, ast_dict_node):
        if isinstance(ast_dict_node, ast.DictComp):
            return self._dict_comprehension_to_dict(ast_dict_node)

        result = {}
        for key_node, value_node in zip(ast_dict_node.keys, ast_dict_node.values):
            if isinstance(value_node, ast.Constant):
                result[ast.literal_eval(key_node)] = ast.literal_eval(value_node)
            elif isinstance(value_node, (ast.Dict, ast.DictComp)):
                result |= self.ast_dict_to_dict(value_node)
        return result

    def _dict_comprehension_to_dict(self, value_node):
        result = {}
        gen = value_node.generators[0]
        target = gen.target
        iterable = None

        def bind_target_to_env(target, item):
            env = {}
            if isinstance(target, ast.Name):
                env[target.id] = item
            elif isinstance(target, ast.Tuple) and isinstance(item, (list, tuple)):
                for elt, val in zip(target.elts, item):
                    if isinstance(elt, ast.Name):
                        env[elt.id] = val
            return env

        def eval_key_value(env):
            key = eval(compile(ast.Expression(value_node.key), "", "eval"), {}, env)
            val = eval(compile(ast.Expression(value_node.value), "", "eval"), {}, env)
            return key, val

        # Case 1: dict.keys(), dict.values(), dict.items()
        if (
            isinstance(gen.iter, ast.Call)
            and isinstance(gen.iter.func, ast.Attribute)
            and isinstance(gen.iter.func.value, ast.Name)
        ):
            variable = gen.iter.func.value.id
            method = gen.iter.func.attr
            assign_node = self.attributes.get(variable)

            if method in ("keys", "values", "items") and isinstance(assign_node.value, ast.Dict):
                try:
                    base_dict = ast.literal_eval(assign_node.value)
                    iterable = getattr(base_dict, method)()
                except Exception as e:
                    raise ValueError(f"Error evaluating dict.{method}() from {variable}: {e}")

        # Case 2: direct variable name like `for x in some_iterable`
        elif isinstance(gen.iter, ast.Name):
            iter_name = gen.iter.id
            assign_node = self.attributes.get(iter_name)
            if isinstance(assign_node, ast.Assign) and isinstance(assign_node.value, (ast.List, ast.Tuple, ast.Dict)):
                iterable = ast.literal_eval(assign_node.value)

        # Iterate and build result
        if iterable is not None:
            for item in iterable:
                try:
                    env = bind_target_to_env(target, item)
                    key, val = eval_key_value(env)
                    result[key] = val
                except Exception as e:
                    raise ValueError(f"Error evaluating dict comprehension: {e}")

        return result
