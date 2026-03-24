import ast
from typing import List
from parser.ast_utils import OPERATOR_MAP
from parser.recipe_visitor import RecipeVisitor
from parser.condition import (
    Condition,
    NoCondition,
    UnknownCondition,
    ConstantCondition,
    VersionCondition,
    ProfileDependentCondition,
)


class ConditionEvaluator:
    conditions = []

    def __init__(self, visitor: RecipeVisitor):
        self.visitor = visitor

    def parse(self, conditions: List) -> Condition:
        self.conditions = conditions
        result = NoCondition()
        for condition in conditions:
            new = self.parse_condition(condition)
            result = result & new
        return result

    def parse_condition(self, condition: ast.AST) -> Condition:
        parsed = UnknownCondition()
        if (
            isinstance(condition, ast.Attribute)
            and isinstance(condition.value, ast.Attribute)
            and isinstance(condition.value.value, ast.Name)
            and condition.value.value.id == "self"
            and condition.value.attr == "options"
        ):
            parsed = self.handle_conditional_option(option=condition.attr)

        # Case: if Version(self.version) <op> "version"
        elif self.visitor.is_version_comparison(condition):
            # TODO
            parsed = VersionCondition(self.visitor.handle_version_comparison(condition))

        # TODO: make this function more recursive and call to itself
        elif isinstance(condition, ast.Compare) and (option_name := self.handle_get_safe(condition.left)):
            parsed = self.handle_conditional_option(
                option=option_name,
                compared_value=condition.comparators[0],
                operator=type(condition.ops[0]),
            )
        elif (
            isinstance(condition, ast.Compare)
            and isinstance(condition.left, ast.Attribute)
            and isinstance(condition.left.value, ast.Attribute)
            and isinstance(condition.left.value.value, ast.Name)
            and condition.left.value.value.id == "self"
        ):
            # Case: self.options.foo == "bar"
            if condition.left.value.attr == "options" and isinstance(condition.left.attr, str):
                parsed = self.handle_conditional_option(
                    option=condition.left.attr,
                    compared_value=condition.comparators[0],
                    operator=type(condition.ops[0]),
                )
            # Case: self.settings comparison
            elif condition.left.value.attr in ("settings", "settings_build", "_settings_build") and isinstance(
                condition.left.attr, str
            ):
                setting = condition.left.attr
                parsed = self.handle_setting_comparison(
                    condition, setting, build_context=condition.left.value.attr != "settings"
                )

        elif isinstance(condition, ast.Constant):
            # Case: True or False
            if isinstance(condition.value, bool):
                parsed = ConstantCondition(condition.value)

        elif isinstance(condition, ast.BoolOp):
            res = NoCondition()
            for value in condition.values:
                other = self.parse_condition(value)
                res = res & other if isinstance(condition.op, ast.And) else res | other
            parsed = res

        elif isinstance(condition, ast.UnaryOp):
            if isinstance(condition.op, ast.Not):
                parsed = ~self.parse_condition(condition.operand)

        # Case: self.options.get_safe("option")
        elif option_name := self.handle_get_safe(condition):
            parsed = self.handle_conditional_option(option=option_name)

        # Case: self.property
        elif (
            isinstance(condition, ast.Attribute)
            and isinstance(condition.value, ast.Name)
            and condition.value.id == "self"
            and (property := self.visitor.properties.get(condition.attr))
            and isinstance(property, ast.Return)
        ):
            parsed = self.parse_condition(property.value)
        # Special case when calling a free function
        elif isinstance(condition, ast.Call) and isinstance(condition.func, ast.Name):
            if (
                condition.func.id == "hasattr"
                and isinstance(condition.args[1], ast.Constant)
                and condition.args[1].value == "settings_build"
            ):
                parsed = ConstantCondition(True)
            elif condition.func.id == "is_msvc":
                parsed = ProfileDependentCondition(admited_settings={"os": ("Windows")})
            elif condition.func.id == "is_apple_os":
                parsed = ProfileDependentCondition(
                    admited_settings={"os": ("Macos", "iOS", "watchOS", "tvOS", "visionOS")}
                )
            elif condition.func.id == "cross_building":
                parsed = ProfileDependentCondition(check_cross_building=True)

        # Case when calling: self.conf.get("<some_conf>")
        elif (
            isinstance(condition, ast.Call)
            and isinstance(condition.func, ast.Attribute)
            and isinstance(condition.func.value, ast.Attribute)
            and isinstance(condition.func.value.value, ast.Name)
            and condition.func.value.value.id == "self"
            and condition.func.value.attr in ("conf", "conf_info")
            and condition.func.attr == "get"
            and isinstance(condition.args[0], ast.Constant)
        ):
            parsed = ProfileDependentCondition(admited_conf=str(condition.args[0].value))

        # print(f"{self.conanfile_path.parent.parent.name}: {ast.unparse(condition)} -> {condition}")
        return parsed.build(ast.unparse(condition))

    def handle_setting_comparison(self, condition: ast.Compare, setting, build_context: bool):
        op = condition.ops[0]
        if (
            isinstance(op, ast.In)
            or isinstance(op, ast.NotIn)
            and isinstance(condition.comparators[0], (ast.List, ast.Tuple))
        ):
            compared_values = [value.value for value in condition.comparators[0].elts]
        elif isinstance(condition.comparators[0], ast.Constant):
            compared_values = condition.comparators[0].value
        else:
            return UnknownCondition()
        return ProfileDependentCondition(
            admited_settings={setting: (compared_values)}, operator=type(op), build_context=build_context
        )

    def handle_conditional_option(self, option, compared_value=True, operator=ast.Eq):
        if option in self.visitor.default_options:
            op_func = OPERATOR_MAP.get(operator)
            value = compared_value if isinstance(compared_value, bool) else ast.literal_eval(compared_value)
            option_value = self.visitor.default_options.get(option, None)
            # TODO take in consideration the profile
            return ConstantCondition(op_func(option_value, value))
        else:
            return UnknownCondition()

    def handle_get_safe(self, condition: ast.AST):
        if (
            isinstance(condition, ast.Call)
            and isinstance(condition.func, ast.Attribute)
            and isinstance(condition.func.value, ast.Attribute)
            and isinstance(condition.func.value.value, ast.Name)
            and condition.func.value.value.id == "self"
            and condition.func.attr == "get_safe"
        ):
            option_name = condition.args[0].value if isinstance(condition.args[0], ast.Constant) else None
            return option_name
        return None

    def __str__(self):
        if len(self.conditions) > 1:
            return " and ".join("(" + ast.unparse(cond) + ")" for cond in self.conditions)
        if len(self.conditions) == 1:
            return ast.unparse(self.conditions[0])
        else:
            return ""
