import json
import os
import sys
from plumbum.cmd import mv, mkdir, rename, sed, rustc, cargo, rm
from plumbum import local

# Path to the root of the robotfindskitten codebase
RFK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'repo'))

sys.path.append(os.path.join(RFK_DIR, '../../../scripts'))
from common import *
import transpile


# List of rust-refactor commands to run.

def mk_select(script, mark='target'):
    return ['select', mark, script]

REFACTORINGS = [
        ['wrapping_arith_to_normal'],
        ['struct_assign_to_update'],
        ['struct_merge_updates'],
        mk_select('crate; child(static);') +
            [';', 'static_collect_to_struct', 'State', 'S'],
        mk_select('crate; desc(fn && !name("main"));') + [';', 'set_visibility', ''],
        mk_select('crate; child(static && name("S"));') + [';'] +
            mk_select('crate; desc(fn && !name("main"));', mark='user') + [';'] +
            ['static_to_local_ref'],
]




idiomize = get_cmd_or_die(config.RREF_BIN)

def run_idiomize(args, mode='inplace'):
    full_args = ['-r', mode] + args + [
            '--', 'src/robotfindskitten.rs', '--crate-type=dylib',
            '-L{rust_libdir}/rustlib/{triple}/lib/'.format(
                rust_libdir=get_rust_toolchain_libpath(),
                triple=get_host_triplet())]

    ld_lib_path = get_rust_toolchain_libpath()

    # don't overwrite existing ld lib path if any...
    if 'LD_LIBRARY_PATH' in local.env:
        ld_lib_path += ':' + local.env['LD_LIBRARY_PATH']

    with local.env(RUST_BACKTRACE='1',
                   LD_LIBRARY_PATH=ld_lib_path):
        with local.cwd(os.path.join(RFK_DIR, 'rust')):
            idiomize[full_args]()


def main():
    os.chdir(RFK_DIR)
    print('in %s' % RFK_DIR)


    # Remove object files that will confuse `transpile`
    rm['-f', 'src/robotfindskitten.o']()


    # Actually translate
    with open('compile_commands.json', 'r') as f:
        transpile.transpile_files(f,
                emit_build_files=False,
                verbose=True)


    # Move rust files into rust/src
    mkdir['-vp', 'rust/src']()
    mv['-v', local.path('src') // '*.rs', 'rust/src/']()


    # Refactor
    for refactor_args in REFACTORINGS:
        print('REFACTOR: %r' % (refactor_args,))
        run_idiomize(refactor_args)


if __name__ == '__main__':
    main()
