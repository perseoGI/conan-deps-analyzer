from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-host-version"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("codec/2.0.0")

    def build_requirements(self):
        self.tool_requires("codec/<host_version>")
