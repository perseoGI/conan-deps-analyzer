from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-local-constant"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        shared_version = "1.4.357.0"
        self.requires(f"first/{shared_version}")
        self.requires(f"second/{shared_version}")
