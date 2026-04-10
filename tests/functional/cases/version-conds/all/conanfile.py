from conan import ConanFile
from conan.tools.scm import Version


class PkgConan(ConanFile):
    name = "fixture-version-conds"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        if Version(self.version) <= "2.0.0":
            self.requires("legacy-x/1.0.0")
        else:
            self.requires("modern-x/9.9.9")
        if Version(self.version) == "2.0.0":
            self.requires("exact-pin/5.5.5")

        if (not Version(self.version) < "2.3.5") and (not Version(self.version) < "3.0.0"):
            self.requires("gap-pkg/1.0.0")
