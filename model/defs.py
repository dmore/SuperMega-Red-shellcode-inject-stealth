from enum import Enum
import os

class FilePath(str):
    pass

# with data/shellcodes/createfile.bin
VerifyFilename: FilePath = FilePath("C:\\Temp\\a")

# Directory structure
PATH_EXES = "data/binary/exes/"
PATH_EXES_MORE = "data/binary/exes_more/"
PATH_SHELLCODES = "data/binary/shellcodes/"
PATH_CARRIER = "data/source/carrier/"
PATH_PAYLOAD = "data/source/payload/"

PATH_DECODER = "data/source/decoder/"
PATH_ANTIEMULATION = "data/source/antiemulation/"
PATH_DECOY = "data/source/decoy/"
PATH_GUARDRAILS = "data/source/guardrails/"
PATH_VIRTUALPROTECT = "data/source/virtualprotect/"

PATH_WEB_PROJECT = "projects/"


class PayloadLocation(Enum):
    CODE = ".text"
    DATA = ".rdata"


class CarrierInvokeStyle(Enum):
    ChangeEntryPoint = "change EntryPoint"
    BackdoorCallInstr = "backdoor Entrypoint"


class FunctionInvokeStyle(Enum):
    peb_walk = "peb_walk"
    iat_reuse = "iat_reuse"

    
class PeRelocEntry():
    def __init__(self, rva: int, base_rva: int, type: str):
        self.rva: int = rva
        self.base_rva: int = base_rva
        self.offset: int = rva - base_rva
        self.type: str = type


    def __str__(self):
        return "PeRelocEntry: rva: 0x{:X} base_rva: 0x{:X} offset: 0x{:X} type: {}".format(
            self.rva, self.base_rva, self.offset, self.type)


class IatEntry():
    def __init__(self, dll_name: str, func_name: str, iat_vaddr: int):
        self.dll_name: str = dll_name
        self.func_name: str = func_name
        self.iat_vaddr: int = iat_vaddr

    def __str__(self):
        return "IatEntry: dll_name: {} func_name: {} iat_vaddr: 0x{:X}".format(
            self.dll_name, self.func_name, self.iat_vaddr)
    


CODE_INJECT_SIZE_CHECK_ADD = 128