from conan import ConanFile

_subs = ("audio", "video")


class PkgConan(ConanFile):
    name = "fixture-options-expand"
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        **{s: [True, False] for s in _subs},
    }
    default_options = {
        "shared": False,
        **{s: True for s in _subs},
    }
    default_options["video"] = False

    def requirements(self):
        if self.options.audio:
            self.requires("audio-dep/1.0.0")
        if not self.options.video:
            self.requires("no-video-dep/2.0.0")
