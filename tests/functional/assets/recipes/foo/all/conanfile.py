from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.files import get, copy, rmdir, replace_in_file
from conan.tools.scm import Version
import os

required_conan_version = ">=2.1"

class PkgConan(ConanFile):
    name = "foo"
    license = "MIT"
    package_type = "library"

    # Binary configuration
    settings = "os", "arch", "compiler", "build_type"

    _subsystems = [
        ("audio", []),
        ("video", []),
    ]
    _pkg_options = {
        "with_libuv": ([True, False], True),
        "libunwind_backtrace": ([True, False], False),
    }

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_podofo": [True, False],
        "with_boost": [True, False],
        "with_libuv": [True, False],
        "with_fmt": [True, False],
        "with_scip": [True, False],
        "with_wasmtime": [True, False],
        "with_zlib": [True, False],
        "with_grpc": [True, False],
        "with_asio": [True, False],
        "with_any_lite": [True, False],
        "foo": ["first", "second"],
        "libunwind_backtrace": [True, False],
        **{subsystem: [True, False] for subsystem, _ in _subsystems},
        "simd_level": ["default"],
    }


    default_options = {
        "with_podofo": True,
        **{ 
            "shared": False,
            "fPIC": True,
            "with_boost": False,
            "with_scip": False,
            "with_wasmtime": True,
            "with_grpc": False,
            "with_asio": False,
            "foo": "first"
        },
        "with_zlib": True,  
        **{"with_any_lite": False},
        **{subsystem: True for subsystem, _ in _subsystems},
        "simd_level": "default",
        **{k: v[1] for k, v in _pkg_options.items()},
    }

    # default_options = {key: False for key in options.keys()}
    default_options["with_fmt"] = True

    implements = ["auto_shared_fpic"]

    @property
    def _required_libuv_version(self):
        return self.conan_data["libuv_version_mapping"][self.version]

    @property
    def _fmt_version(self): #mapping of bgfx version to required/used bx version
        return {"3.0.0": "11.2.0",
                "2.5.0": "11.1.4",
                "2.0.0": "11.1.3"}

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def requirements(self):
        # if Version(self.version) <= "2.5.0":
        #     self.requires("boost/1.73.0")
        # else:
        #     self.requires("boost/1.83.0")

        if Version(self.version) <= "2.5.0":
            if self.options.with_zlib:
                self.requires("asio/1.16.1")
            else:
                self.requires("boost/1.73.0")
        else:
            if self.options.with_zlib:
                self.requires("asio/1.28.1")
            else:
                self.requires("boost/1.83.0")
        
        # Access to property which return a map
        # if self.settings.os != 'Android':
        # if self.settings.os in ("Linux", "Macos", "Windows") and self.settings_build.compiler == "gcc":
            # and self.version == "2.0.0":

        # if not cross_building(self):
            # self.requires("aws-c-common/0.11.0", transitive_headers=True, transitive_libs=True)
        # if self.settings.os == "Android":
        #     self.requires("libuv/1.44.2")
        #
        # if Version(self.version) == "2.5.0":
        #     self.requires(f"fmt/{self._fmt_version[self.version]}", transitive_headers=True)

        # loaders_opt = str(self.options.foo)
        # if loaders_opt in ("all", "first"):
        #     self.requires("libjpeg-turbo/3.0.2")
        # if self.options.with_podofo:
        # if (self._settings_build.os == "Windows" and self.options.with_podofo):
        #     self.requires("gnu-config/cci.20201022")

        # if not self.conf.get("tools.microsoft.bash:path", check_type=str):
        #     self.requires("wt/4.11.2")

        # if is_msvc(self):
        # if is_apple_os(self):
        #     self.requires("gnu-config/cci.20201022")
        # if self.settings.os != "Windows":
        # if self.settings.os in ('Windows', 'Linux', 'Macos'):
        #     self.requires("odbc/2.3.11", transitive_headers=True)
        # if self.settings.os != "Windows":
        #     self.requires("test/2.3.11", transitive_headers=True)

    def build_requirements(self):
        pass
        # loaders_opt = str(self.options.foo)
        # if loaders_opt in ("all", "first"):
        #     self.tool_requires("test/1")
    #     self.tool_requires("libzip/<host_version>")
    #     self.tool_requires(f"test/{self.version}")
    #     if self.settings.os == "Windows":
    #         self.tool_requires("cmake/3.15")
    #     self.tool_requires(f"{self.name}/{self.version}")
    #     self.tool_requires("libpng/[>=1.6.32 <1.6.39]")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "set(CMAKE_CXX_STANDARD",
                        "#set(CMAKE_CXX_STANDARD")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder)

        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["pkg"]

