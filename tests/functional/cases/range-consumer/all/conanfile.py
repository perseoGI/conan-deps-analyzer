from conan import ConanFile


class RangeConsumerConan(ConanFile):
    name = "range-consumer"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # Ref names match sibling case folder names under cases/ (used by resolve_version_range).
        self.requires("map/[>=1.5 <3]")
        self.requires("property-fstring/[>=2.5 <4]")
        self.requires("version-conds/[>=1.5 <3]")
