from conan import ConanFile


class PkgConan(ConanFile):
    name = "fixture-pkgid-patch"
    settings = "os", "arch", "compiler", "build_type"
    package_id_non_embed_mode = "patch_mode"
