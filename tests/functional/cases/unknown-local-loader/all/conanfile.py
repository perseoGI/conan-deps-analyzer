from conan import ConanFile


class PkgConan(ConanFile):
    name = "unknown-local-loader"
    settings = "os", "arch", "compiler", "build_type"
    options = {"slot": ["first", "second"]}
    default_options = {"slot": "first"}

    def requirements(self):
        x = str(self.options.slot)
        if x in ("first", "all"):
            self.requires("u-dep/1.0.0")
