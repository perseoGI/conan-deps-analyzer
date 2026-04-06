from conan import ConanFile
from conan.tools.scm import Version
from conan.tools.apple import is_apple_os
from conan.tools.microsoft import is_msvc
from conan.tools.build import cross_building


class PkgConan(ConanFile):
    name = "fixture-mixed-conds"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "with_zlib": [True, False],
        "with_podofo": [True, False],
        "loader_slot": ["first", "second", "all"],
    }
    default_options = {
        "shared": False,
        "with_zlib": True,
        "with_podofo": True,
        "loader_slot": "first",
    }

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def requirements(self):
        # Version + option nesting (foo 91-100 style)
        if Version(self.version) <= "2.0.0":
            if self.options.with_zlib:
                self.requires("mix-asio/1.16.1")
            else:
                self.requires("mix-nolib-low/9.9.9")
        else:
            if self.options.with_zlib:
                self.requires("mix-asio/1.28.1")
            else:
                self.requires("mix-nolib-high/8.8.8")

        if not cross_building(self):
            self.requires("mix-cross-safe/1.0.0")

        if self.settings.os == "Android":
            self.requires("mix-droid/1.0.0")

        if is_msvc(self):
            self.requires("mix-msvc/1.0.0")

        if is_apple_os(self):
            self.requires("mix-apple/1.0.0")

        if self._settings_build.os == "Windows" and self.options.with_podofo:
            self.requires("mix-win-gnu/1.0.0")

        if not self.conf.get("tools.microsoft.bash:path", check_type=str):
            self.requires("mix-wt/4.1.0")

        # Direct option membership (foo often uses str(self.options.foo) then `in`; local name => UnknownCondition).
        if self.options.loader_slot in ("all", "first"):
            self.requires("mix-jpeg-inline/3.0.2")

        if self.settings.os in ("Windows", "Linux", "Macos"):
            self.requires("mix-odbc/2.3.11")

        if self.settings.os != "Windows":
            self.requires("mix-posix/2.3.11")
