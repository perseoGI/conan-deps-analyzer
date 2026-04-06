from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-min"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("tree-sitter/1.0.0", transitive_headers=True, transitive_libs=True)
