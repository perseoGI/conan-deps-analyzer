from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-property-fstring"
    settings = "os", "arch", "compiler", "build_type"

    @property
    def _bx_map(self):
        return {
            "1.0.0": "10.1.0",
            "2.0.0": "20.2.0",
            "3.0.0": "30.3.0",
        }

    def requirements(self):
        self.requires(f"bx-lib/{self._bx_map[self.version]}")
