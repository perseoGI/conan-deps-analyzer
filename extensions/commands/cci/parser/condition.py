import ast
from abc import ABC, abstractmethod
from typing import Dict, Iterable
from conan.tools.scm import Version
from conan.internal.model.profile import Profile


class Condition(ABC):
    _printable: bool = True

    @abstractmethod
    def evaluate(
        self, version: str | None = None, profile_host: Profile | None = None, profile_build: Profile | None = None
    ) -> bool:
        pass

    def build(self, condition: str) -> "Condition":
        self.condition = condition
        return self

    @property
    def printable(self) -> bool:
        """
        Whether this condition should be printed in the output or not, only VersionCondition when is False should not be printed.
        AndCondition and OrCondition depend on their children.
        """
        return self._printable

    def __invert__(self) -> "Condition":
        return self

    def __and__(self, other: "Condition") -> "Condition":
        return AndCondition(self, other)

    def __or__(self, other: "Condition") -> "Condition":
        return OrCondition(self, other)

    def __str__(self) -> str:
        return self.condition


class NoCondition(Condition):
    """
    Represents a neutral/undefined condition — could be treated as 'always true' or skipped.
    """

    def evaluate(self, version=None, profile_host: Profile | None = None, profile_build: Profile | None = None) -> bool:
        return True  # or `return None` if you want to treat it as unset

    def __str__(self) -> str:
        return ""

    def __and__(self, other: Condition) -> Condition:
        return other

    def __or__(self, other: "Condition") -> "Condition":
        return other


class UnknownCondition(Condition):
    def evaluate(self, version=None, profile_host: Profile | None = None, profile_build: Profile | None = None) -> bool:
        return False  # It will never be evaluated


class ConstantCondition(Condition):
    def __init__(self, value: bool):
        self.value = value

    def evaluate(self, version=None, profile_host: Profile | None = None, profile_build: Profile | None = None) -> bool:
        return self.value

    def __invert__(self) -> Condition:
        self.value = not self.value
        return self


class VersionCondition(Condition):
    def __init__(self, version_map: Dict[str, bool]):
        self.version_map = version_map

    def evaluate(self, version=None, profile_host: Profile | None = None, profile_build: Profile | None = None) -> bool:
        result = self.version_map[Version(version)]
        self._printable = result
        return result

    def __invert__(self) -> Condition:
        self.version_map = {k: not v for k, v in self.version_map.items()}
        return self


class ProfileDependentCondition(Condition):
    """
    Condition that depends on profile settings. You must provide the required settings to satisfy the condition.
    """

    DEFAULT_SETTINGS = {
        "os": ("Windows", "Linux", "Macos"),
        "arch": ("x86_64", "armv8"),
        "compiler": ("gcc", "Visual Studio", "apple-clang"),
        "build_type": ("Release", "Debug"),
    }

    DEFAULT_CONF = {"tools.microsoft.bash:path": False, "tools.gnu:pkg_config": False}

    def __init__(
        self,
        admited_settings: Dict[str, Iterable[str]] = {},
        admited_conf: str | None = None,
        operator=ast.Eq,
        build_context: bool = False,
        check_cross_building: bool = False,
    ):
        self.admited_settings = admited_settings
        self.admited_conf = admited_conf
        self.inverted = False
        self.operator = operator
        self.build_context = build_context  # If True, use settings_build instead of settings
        self.check_cross_building = check_cross_building

    def evaluate(self, version=None, profile_host: Profile | None = None, profile_build: Profile | None = None) -> bool:
        if self.admited_settings:
            return self.evaluate_settings(profile_host, profile_build)
        if self.admited_conf:
            return self.evaluate_conf(profile_host)
        if self.check_cross_building:
            return self.evaluate_cross_build(profile_host, profile_build)

    def evaluate_settings(self, profile_host: Profile | None, profile_build: Profile | None) -> bool:
        # Check that all required settings are present in the profile
        profile = profile_build if self.build_context else profile_host
        settings = profile.settings if profile else self.DEFAULT_SETTINGS

        for setting, valid_values in self.admited_settings.items():
            possible_values = settings.get(setting)
            if not possible_values:
                return True if self.inverted else False
            possible_values = set([possible_values]) if isinstance(possible_values, str) else set(possible_values)
            valid_values = set([valid_values]) if isinstance(valid_values, str) else set(valid_values)
            intersection = possible_values.intersection(valid_values)
            if self.operator == ast.NotIn:
                result = len(intersection) != len(valid_values) if len(possible_values) > 1 else len(intersection) == 0
            elif self.operator == ast.NotEq:
                result = intersection if len(possible_values) > 1 else not intersection
            else:
                result = any(intersection)
            if not result:
                return True if self.inverted else False
        return False if self.inverted else True

    def evaluate_conf(self, profile_host: Profile | None) -> bool:
        confs = profile_host.conf if profile_host else self.DEFAULT_CONF
        conf_present = confs.get(self.admited_conf, False)
        return not conf_present if self.inverted else conf_present

    def evaluate_cross_build(self, profile_host: Profile | None, profile_build: Profile | None) -> bool:
        if not profile_host or not profile_build:
            return True  # Default CCI
        host_os = profile_host.settings.get("os")
        build_os = profile_build.settings.get("os")
        host_arch = profile_host.settings.get("arch")
        build_arch = profile_build.settings.get("arch")
        cross_bulding = build_os != host_os or build_arch != host_arch
        return not cross_bulding if self.inverted else cross_bulding

    def __invert__(self) -> Condition:
        self.inverted = not self.inverted
        return self


class AndCondition(Condition):
    def __init__(self, cond: Condition, *conditions):
        self.conditions = [cond] + list(conditions)

    def evaluate(self, version=None, profile_host: Profile | None = None, profile_build: Profile | None = None) -> bool:
        return all(cond.evaluate(version, profile_host, profile_build) for cond in self.conditions)

    @property
    def printable(self) -> bool:
        return all(cond.printable for cond in self.conditions)

    def __and__(self, other: Condition) -> Condition:
        self.conditions.append(other)
        return self

    def __invert__(self) -> Condition:
        return OrCondition(*(~cond for cond in self.conditions))

    def __str__(self):
        if len(self.conditions) > 1:
            return " and ".join("(" + str(cond) + ")" for cond in self.conditions)
        if len(self.conditions) == 1:
            return self.conditions[0].condition
        else:
            return ""


class OrCondition(Condition):
    def __init__(self, cond: Condition, *conditions):
        self.conditions = [cond] + list(conditions)

    def evaluate(self, version=None, profile_host: Profile | None = None, profile_build: Profile | None = None) -> bool:
        return any(cond.evaluate(version, profile_host, profile_build) for cond in self.conditions)

    @property
    def printable(self) -> bool:
        return any(cond.printable for cond in self.conditions)

    def __or__(self, other: Condition) -> Condition:
        self.conditions.append(other)
        return self

    def __invert__(self) -> Condition:
        return AndCondition(*(~cond for cond in self.conditions))

    def __str__(self):
        if len(self.conditions) > 1:
            return " or ".join("(" + str(cond) + ")" for cond in self.conditions)
        if len(self.conditions) == 1:
            return self.conditions[0].condition
        else:
            return ""
