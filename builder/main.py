from SCons.Script import DefaultEnvironment
from platformio.util import get_systype

env = DefaultEnvironment()

env.Replace(
    _BINPREFIX="",
    AR="${_BINPREFIX}ar",
    AS="${_BINPREFIX}as",
    CC="${_BINPREFIX}gcc",
    CXX="${_BINPREFIX}g++",
    GDB="${_BINPREFIX}gdb",
    OBJCOPY="${_BINPREFIX}objcopy",
    RANLIB="${_BINPREFIX}ranlib",
    SIZETOOL="${_BINPREFIX}size",

    SIZEPRINTCMD='$SIZETOOL $SOURCES'
)

if get_systype() == "darwin_x86_64":
    env.Replace(
        _BINPREFIX="x86_64-pc-linux-"
    )


target_bin = env.BuildProgram()
exec_target = env.AddPlatformTarget("exec", target_bin, [ env.VerboseAction("./$SOURCE", "Erasing...") ], "Execute the built program")

#
# Target: Define targets
#
Default(target_bin)

