from enum import Enum
import os

class FilePath(str):
    pass

# with shellcodes/createfile.bin
VerifyFilename: FilePath = r'C:\Temp\a'

# Correlated with real template files
# in plugins/

class AllocStyle(Enum):
    RWX = "rwx_1"
    #RW_X = "rw_x"
    #REUSE = "reuse"

class DecoderStyle(Enum):
    PLAIN_1 = "plain_1"
    XOR_1 = "xor_1"

class ExecStyle(Enum):
    CALL = "direct_1"
    #JMP = 2,
    #FIBER = 3,

class DataRefStyle(Enum):
    APPEND = 1

#class InjectStyle(Enum):
    
class SourceStyle(Enum):
    peb_walk = "peb_walk"
    iat_reuse = "iat_reuse"


build_dir = "build"

main_c_file = os.path.join(build_dir, "main.c")
main_asm_file = os.path.join(build_dir, "main.asm")
main_exe_file = os.path.join(build_dir, "main.exe")
main_shc_file = os.path.join(build_dir, "main.bin")