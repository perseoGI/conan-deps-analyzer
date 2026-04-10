from conan import ConanFile
from conan.tools.scm import Version


class ParserGapsConan(ConanFile):
    name = "parser-gaps"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # Edge case: compound (not Version ...) and (...); ConditionEvaluator does not model this yet.
        if (not Version(self.version) < "2.3.5") and (not Version(self.version) < "3.0.0"):
            self.requires("gap-pkg/1.0.0")
