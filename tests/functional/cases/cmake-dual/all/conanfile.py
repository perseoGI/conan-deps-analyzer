from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-cmake-dual"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("cmake/3.20")

    def build_requirements(self):
        self.tool_requires("cmake/3.20")
