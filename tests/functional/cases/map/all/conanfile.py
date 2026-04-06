from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-map"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(f"dep-pkg/{self.conan_data['map'][self.version]}")

    def build_requirements(self):
        self.tool_requires(f"{self.name}/{self.version}")
