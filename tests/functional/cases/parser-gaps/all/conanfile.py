from conan import ConanFile
from conan.tools.scm import Version


class ParserGapsConan(ConanFile):
    name = "parser-gaps"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # Gap 1: ast.BinOp (+) — dependency_extractor has no handler (foo-style concat).
        self.requires("tree-sitter/" + "1.0.0")

        # Gap 2: compound (not Version ...) and (...); evaluator does not model this shape.
        if (not Version(self.version) < "2.3.5") and (not Version(self.version) < "3.0.0"):
            self.requires("gap-pkg/1.0.0")

        # Also the variable + conandata form (still BinOp / local dep string).
        dep = "tree-sitter-alt/" + self.conan_data["tree-sitter-version"][self.version]
        self.requires(dep)
