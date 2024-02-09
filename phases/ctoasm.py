from helper import *
from config import config
import os
import pprint

from model import *


def make_c_to_asm(c_file, asm_file, payload_len, capabilities: ExeCapabilities):
    print("--[ C to ASM: {} -> {} ]".format(c_file, asm_file))

    asm = {
        "initial": "",
        "cleanup": "",
        "fixup": "",
    }

    # Phase 1: Compile
    print("---[ Compile: {} ]".format(c_file))
    run_process_checkret([
            config.get("path_cl"),
            "/c",
            "/FA",
            "/GS-",
            "/Fa{}/".format(os.path.dirname(c_file)),
            c_file,
    ])
    if not os.path.isfile(asm_file):
        print("Error: Compiling failed")
        return
    asm["initial"] = file_readall_text(asm_file)

    # Phase 2: Assembly cleanup
    asm_clean_file = asm_file + ".clean"
    print("---[ Cleanup: {} ]".format(asm_file))
    run_process_checkret([
        config.get("path_masmshc"),
        asm_file,
        asm_clean_file,
    ])
    if not os.path.isfile(asm_clean_file):
        print("Error: Cleanup filed")
        return
    else:
        shutil.move(asm_clean_file, asm_file)
        asm["cleanup"] = file_readall_text(asm_file)

    # Phase 2: Assembly fixup
    print("---[ Fixup  : {} ]".format(asm_file))
    if not fixup_asm_file(asm_file, payload_len, capabilities):
        print("Error: Fixup failed")
        return
    else:
        asm["fixup"] = file_readall_text(asm_file)

    return asm


def bytes_to_asm_db(byte_data):
    # Convert each byte to a string in hexadecimal format suffixed with 'h'
    hex_values = [f"0{byte:02x}H" for byte in byte_data]
    # Join the hex values into a single string with ', ' as separator
    formatted_string = ', '.join(hex_values)
    return "\tDB " + formatted_string


def fixup_asm_file(filename, payload_len, capabilities: ExeCapabilities):
    with open(filename, 'r', encoding='utf-8') as asmfile:
        lines = asmfile.readlines()

    #pprint.pprint(exe_capabilities)

    # FUCK
    for idx, line in enumerate(lines):
        if "jmp\tSHORT" in lines[idx]:
            lines[idx] = lines[idx].replace("SHORT", "")

    # do IAT reuse
    for idx, line in enumerate(lines):
        # Remove definition: 
        #   EXTRN	__imp_MessageBoxW:PROC
        if "EXTRN	__imp_" in lines[idx]:
            lines[idx] = "; " + lines[idx]
            continue

        # Fix call
        if "call" in lines[idx] and "__imp_" in lines[idx]:
            func_name = lines[idx][lines[idx].find("__imp_")+6:].rstrip()
            print("    > Replace func name: {}".format(func_name))

            exeCapability = capabilities.get(func_name)
            if exeCapability == None:
            #if func_name not in exe_capabilities or exe_capabilities[func_name] == None:
                print("Error Capabilities not: {}".format(func_name))
            else:
                randbytes: bytes = os.urandom(6)
                lines[idx] = bytes_to_asm_db(randbytes) + "\r\n"
                exeCapability.id = randbytes
                #func_addr = exe_capabilities[func_name]
                #lines[idx] = "\tcall  main\r\n"
                #lines[idx] = "\tcall  rax\r\n"
                #lines.insert(idx, "\tmov rax, [rax]\r\n")
                #lines.insert(idx, "\tmov rax, {:X}H\r\n".format(func_addr))

            #print("    > Replace__imp_MessageBoxW at line: {}".format(idx))
            #lines[idx] = lines[idx].replace("__imp_MessageBoxW", "ds:[0x123]")
        
    # replace external reference with shellcode reference
    for idx, line in enumerate(lines): 
        if "dobin" in lines[idx]:
            print("    > Replace external reference at line: {}".format(idx))
            lines[idx] = lines[idx].replace(
                "mov	r8, QWORD PTR dobin",
                "lea	r8, [shcstart]"
            )

    # replace payload length
    for idx, line in enumerate(lines): 
        if "11223344" in lines[idx]:
            print("    > Replace payload length at line: {}".format(idx))
            lines[idx] = lines[idx].replace("11223344", str(payload_len+1))
            break
            
    # add label at end of code
    for idx, line in enumerate(lines): 
        if lines[idx].startswith("END"):
            print("    > Add end of code label at line: {}".format(idx))
            lines.insert(idx-1, "shcstart:\r\n")
            lines.insert(idx, "\tnop\r\n")
            break
    
    with open(filename, 'w') as asmfile:
        asmfile.writelines(lines)

    return True