import os
import sys
import traceback

from . import mel_parser
from . import semantic
from . import mel_ast
from . import msil


def execute(prog: str, msil_only: bool = False, jbc_only: bool = False, file_name: str = None) -> None:
    try:
        prog = mel_parser.parse(prog)
    except Exception as e:
        # print('Ошибка: {}'.format(e.message), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        exit(1)

    try:
        scope = semantic.prepare_global_scope()
        prog.semantic_check(scope)
        # print(*prog.tree, sep=os.linesep)
        if not (msil_only or jbc_only):
            print(*prog.tree, sep=os.linesep)
            # print()
    except semantic.SemanticException as e:
        # print('Ошибка: {}'.format(e.message), file=sys.stderr)
        exit(2)

    if not jbc_only:
        try:
            gen = msil.CodeGenerator()
            gen.msil_gen_program(prog)
            print(*gen.code, sep=os.linesep)
        except msil.MsilException or Exception as e:
            print('Ошибка: {}'.format(e.message), file=sys.stderr)
            exit(3)
