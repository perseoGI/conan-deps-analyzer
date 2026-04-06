from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-conandata-prop"
    settings = "os", "arch", "compiler", "build_type"

    @property
    def _sidecar_dep_ver(self):
        return self.conan_data["sidecar"][self.version]

    def requirements(self):
        self.requires(f"sidecar/{self._sidecar_dep_ver}")
