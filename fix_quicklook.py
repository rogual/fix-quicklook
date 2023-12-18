#!/usr/bin/env python3

'''

fix-quicklook

    Find all running QuickLookUIService instances on the system and patch them to
    remove the rounded corners from image previews.

    The patch is in-memory only and does not modify any binaries. It must be
    applied again for each new QuickLook process.

    TODO: Maybe add an option to make this script set itself up to run at login.

    TODO: Sometimes the system creates new QuickLook processes. Investigate
    whether they need to be patched too, and maybe add a way of automatically
    patching them.


Caveats:

    This entire script will not work if SIP is enabled. This kind of thing is
    exactly what SIP is supposed to prevent.

    Only tested on MacOS Ventura 13.5


Implementation notes:

    - Uses dlopen to load the image plugin because QuickLook lazily loads plugins and
    it might not have been loaded yet. Fortunately, dlopen'ing a dylib is enough
    to register its classes with the ObjC runtime.

    - Looks a bit more complicated than it is, mostly because of having to load itself
    into the LLDB process. Perhaps an LLDB expert could write this more simply.


Author:

    Robin Allen <r@foon.uk>

'''


# If we're not inside LLDB yet
if __name__ == '__main__':
    import io
    import os
    import sys
    import subprocess

# If we're inside LLDB
else:
    import lldb
    import struct
    import sys

    target = None
    process = None
    patched_pids = []


def patch_updateCornerRadius():
    '''Patch updateCornerRadius to return immediately without doing anything.'''
    updateCornerRadius = get_symbol_address('-[IKImageContentView updateCornerRadius]')
    write_instruction(updateCornerRadius, 0xd65f03c0)

    
def patch_enableBorder():
    '''Patch enableBorder to jump straight to disableBorder.'''
    enableBorder = get_symbol_address('-[QLDisplayBundleViewController enableBorder]')
    disableBorder = get_symbol_address('-[QLDisplayBundleViewController disableBorder]')

    jump_offset_bytes = disableBorder - enableBorder
    jump_offset_insns = jump_offset_bytes // 4

    jump_insn = (5 << 26) | sign_extend(jump_offset_insns, 26)

    write_instruction(enableBorder, jump_insn)


def get_symbol_address(name):
    symbol_context, = target.FindSymbols(name)
    return symbol_context.symbol.addr.GetLoadAddress(target)


def write_instruction(address, insn):
    e = lldb.SBError()
    process.WriteMemory(
        address,
        struct.pack('<I', insn), e
    )
    assert e.Success()


def sign_extend(val, nbits):
    return (val + (1 << nbits)) % (1 << nbits)


def lldb_script():
    global target
    global process

    target = lldb.debugger.GetSelectedTarget()
    process = target.GetProcess()

    patch_updateCornerRadius()
    patch_enableBorder()
    pid = process.GetProcessInfo().GetProcessID()
    patched_pids.append(pid)


def print_status(pids):
    n = len(patched_pids)
    if n == len(pids):
        print(f"\nSuccess: {n} QuickLook processes patched.")
        return

    print("\nFailed to patch all QuickLook processes:")
    for pid in pids:
        print(f"  {pid: >7}:", end=" ")
        if pid in patched_pids:
            print("[ OK ] Patched")
        else:
            print("[FAIL] Failed to patch")
    lldb.debugger.HandleCommand('quit 1')


def main():

    # Check we're on Apple Silicon
    arch = subprocess.check_output(['/usr/bin/uname', '-m']).decode('utf-8').strip()
    if arch != 'arm64':
        print(f"This script only supports Apple Silicon.")
        print(f"  Required arch: arm64")
        print(f"      Your arch: {arch}")
        sys.exit(1)
    
    # Check SIP is disabled
    csrstatus = subprocess.check_output(['/usr/bin/csrutil', 'status']).decode('utf-8').strip()
    if csrstatus == 'System Integrity Protection status: enabled.':
        print("This script cannot work because SIP is enabled.")
        sys.exit(1)
    elif csrstatus == 'System Integrity Protection status: disabled.':
        pass
    else:
        print("WARNING: Unable to determine whether SIP is enabled.")

    # We'll need this script's own path so we can tell LLDB to import it
    script_path = os.path.realpath(__file__)

    # We'll need the QL plugins path so we can force-load the Image plugin
    # before we do our thing (we need some of its classes to be available)
    plugins = '/System/Library/Frameworks/QuickLookUI.framework/Versions/A/PlugIns'

    # Find all QuickLookUI processes
    try:
        pids = [
            int(x)
            for x in
            subprocess.check_output('pgrep -x QuickLookUIService', shell=True).decode('utf-8').split()
        ]
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            print("QuickLookUIService is not running. Can't do anything.")
            sys.exit(1)
        raise

    if len(pids) > 1:
        print(f"Fixing {len(pids)} QuickLook instances")

    # Concoct an LLDB script that visits them all and fixes them
    run_per_pid = f'''
p (void *)dlopen("{plugins}/Image.qldisplay/Contents/MacOS/Image", 2);
script -- import fix_quicklook; fix_quicklook.lldb_script()
'''
    
    script = f"command script import '{script_path}'\n"
    for i, pid in enumerate(pids):
        script += f'\nattach {pid}\n' + run_per_pid + '\ncontinue\ndetach\n'
    script += f'script -- import fix_quicklook; fix_quicklook.print_status({pids})\n'

    # Run the LLDB script
    p = subprocess.Popen(
        ['/usr/bin/lldb', '--batch'],
        stdin=subprocess.PIPE
    )
    p.communicate(input=script.encode('utf-8'))
    if p.returncode != 0:
        print(f"LLDB failed with code {p.returncode}")
        sys.exit(p.returncode)


if __name__ == '__main__':
    main()
