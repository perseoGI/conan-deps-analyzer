from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-pkgid-tool-consumer"
    settings = "os", "arch", "compiler", "build_type"

    def build_requirements(self):
        self.tool_requires("pkgid-patch/[>=1.0 <2]")
