from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-conandata-nested"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        required_version = self.conan_data["version_mappings"][self.version]["sidecar"]
        self.requires(f"sidecar/{required_version}")
