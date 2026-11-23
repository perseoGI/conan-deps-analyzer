from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-pkgid-patch-consumer"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("pkgid-patch/[>=1.0 <2]")
