from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-cond"
    settings = "os", "arch", "compiler", "build_type"
    options = {"with_extra": [True, False]}
    default_options = {"with_extra": True}

    def requirements(self):
        if self.options.with_extra:
            self.requires("extra-pkg/1.0.0")
