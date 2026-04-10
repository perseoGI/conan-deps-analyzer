from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-variable-requires"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        dep = f"myrequirement/{self.conan_data['myrequirement_version'][self.version]}"
        self.requires(dep)

        self.requires("tree-sitter/" + "1.0.0")

        dep_binop = "tree-sitter-alt/" + self.conan_data["tree-sitter-version"][self.version]
        self.requires(dep_binop)

    def build_requirements(self):
        tool_dep = "cmake/3.15"
        self.tool_requires(tool_dep)
