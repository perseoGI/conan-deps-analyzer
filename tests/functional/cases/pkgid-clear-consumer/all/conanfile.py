from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-pkgid-clear-consumer"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("pkgid-patch/[>=1.0 <2]")

    def package_id(self):
        self.info.requires.clear()
