from typing import List, Union, Any

from . import visitor
from .semantic import BaseType, TypeDesc, ScopeType, BinOp
from .mel_ast import AstNode, LiteralNode, IdentNode, BinOpNode, TypeConvertNode, CallNode, \
    VarsNode, FuncNode, AssignNode, ReturnNode, IfNode, ForNode, StmtListNode, WhileNode, VarNode

RUNTIME_CLASS_NAME = 'CompilerDemo.Runtime'
PROGRAM_CLASS_NAME = 'Program'

MSIL_TYPE_NAMES = {
    BaseType.VOID: 'void',
    BaseType.INT: 'int32',
    BaseType.FLOAT: 'float64',
    BaseType.BOOL: 'bool',
    BaseType.STR: 'string'
}


class CodeLabel:
    def __init__(self):
        self.index = None

    def __str__(self):
        return f'L_{self.index}'


class CodeLine:
    def __init__(self, code: str, *params: Union[str, CodeLabel], label: CodeLabel = None):
        self.code = code
        self.label = label
        self.params = params

    def __str__(self):
        line = ''
        if self.label:
            line += str(self.label) + ': '
        line += self.code
        for p in self.params:
            line += ' ' + str(p)
        return line


class MsilException(Exception):
    """Класс для исключений во время генерации MSIL
       (на всякий случай, пока не используется)
    """

    def __init__(self, message, **kwargs: Any) -> None:
        self.message = message


def find_vars_decls(node: AstNode) -> List[VarNode]:
    vars_nodes: List[VarNode] = []

    def find(node: AstNode) -> None:
        for n in (node.childs or []):
            if isinstance(n, VarNode):
                vars_nodes.append(n)
            else:
                find(n)

    find(node)
    return vars_nodes


def get_msil_type(type) -> str:
    if type == "Int":
        return "int32"
    if type == "Float":
        return "float64"
    if type == "String":
        return "string"
    if type == "Boolean":
        return "bool"


class CodeGenerator:
    def __init__(self):
        self.code_lines: List[CodeLine] = []
        self.indent = ''

    def add(self, code: str, *params: Union[str, int, CodeLabel], label: CodeLabel = None):
        if len(code) > 0 and code[-1] == '}':
            self.indent = self.indent[2:]
        self.code_lines.append(CodeLine(self.indent + str(code), *params, label=label))
        if len(code) > 0 and code[-1] == '{':
            self.indent = self.indent + '  '

    @property
    def code(self) -> [str, ...]:
        index = 0
        for cl in self.code_lines:
            line = cl.code
            if cl.label:
                cl.label.index = index
                index += 1
        code: List[str] = []
        for cl in self.code_lines:
            code.append(str(cl))
        return code

    def start(self) -> None:
        self.add('.assembly program')
        self.add('{')
        self.add('}')
        self.add('.class public ' + PROGRAM_CLASS_NAME)
        self.add('{')

    def end(self) -> None:
        self.add('}')

    @visitor.on('AstNode')
    def msil_gen(self, AstNode):
        """
        Нужен для работы модуля visitor (инициализации диспетчера)
        """
        pass

    @visitor.when(LiteralNode)
    def msil_gen(self, node: LiteralNode) -> None:
        if node.node_type.base_type == BaseType.INT:
            self.add('ldc.i4', node.value)
        elif node.node_type.base_type == BaseType.FLOAT:
            self.add('ldc.r8', str(node.value))
        elif node.node_type.base_type == BaseType.BOOL:
            self.add('ldc.i4', 1 if node.value else 0)
        elif node.node_type.base_type == BaseType.STR:
            self.add(f'ldstr "{node.value}"')
        else:
            pass

    @visitor.when(IdentNode)
    def msil_gen(self, node: IdentNode) -> None:
        if node.node_ident.scope == ScopeType.LOCAL:
            self.add('ldloc', node.node_ident.index)
        elif node.node_ident.scope == ScopeType.PARAM:
            self.add('ldarg', node.node_ident.index)
        elif node.node_ident.scope in (ScopeType.GLOBAL, ScopeType.GLOBAL_LOCAL):
            self.add(
                f'ldsfld {MSIL_TYPE_NAMES[node.node_ident.type.base_type]} {PROGRAM_CLASS_NAME}::_gv{node.node_ident.index}')

    @visitor.when(AssignNode)
    def msil_gen(self, node: AssignNode) -> None:
        self.msil_gen(node.val)
        var = node.var
        if var.node_ident.scope == ScopeType.LOCAL:
            self.add('stloc', var.node_ident.index)
        elif var.node_ident.scope == ScopeType.PARAM:
            self.add('starg', var.node_ident.index)
        elif var.node_ident.scope in (ScopeType.GLOBAL, ScopeType.GLOBAL_LOCAL):
            self.add(f'stsfld {MSIL_TYPE_NAMES[var.node_ident.type.base_type]} Program::_gv{var.node_ident.index}')

    @visitor.when(VarsNode)
    def msil_gen(self, node: VarsNode) -> None:
        for var in node.vars:
            if isinstance(var, AssignNode):
                self.msil_gen(var)

    @visitor.when(VarNode)
    def msil_gen(self, node: VarNode):
        if node.var is not None:
            if node.type.name == "String":
                self.add('ldstr', node.var)
                self.add(f'stsfld string Program::_gv{node.ident.node_ident.index}')
            elif node.type.name == "Float":
                self.add('ldc.r8', node.var)
                self.add(f'stsfld float64 Program::_gv{node.ident.node_ident.index}')
            elif node.type.name == "Boolean":
                if node.var.literal == "true":
                    node.var.literal = "1"
                self.add('ldc.r8', node.var)
                self.add(f'stsfld bool Program::_gv{node.ident.node_ident.index}')
            else:
                self.add('ldc.i4', node.var)
                self.add(f'stsfld int32 Program::_gv{node.ident.node_ident.index}')

        # Генерация кода для инициализации переменной
        if isinstance(node.var, AssignNode):
            node.var.msil_gen(self)

    @visitor.when(BinOpNode)
    def msil_gen(self, node: BinOpNode) -> None:
        self.msil_gen(node.arg1)
        self.msil_gen(node.arg2)
        if node.op == BinOp.NEQUALS:
            if node.arg1.node_type == TypeDesc.STR:
                self.add('call bool [mscorlib]System.String::op_Inequality(string, string)')
            else:
                self.add('ceq')
                self.add('ldc.i4.0')
                self.add('ceq')
        if node.op == BinOp.EQUALS:
            if node.arg1.node_type == TypeDesc.STR:
                self.add('call bool [mscorlib]System.String::op_Equality(string, string)')
            else:
                self.add('ceq')
        elif node.op == BinOp.GT:
            if node.arg1.node_type == TypeDesc.STR:
                self.add(
                    f'call {MSIL_TYPE_NAMES[BaseType.INT]} class {RUNTIME_CLASS_NAME}::compare({MSIL_TYPE_NAMES[BaseType.STR]}, {MSIL_TYPE_NAMES[BaseType.STR]})')
                self.add('ldc.i4.0')
                self.add('cgt')
            else:
                self.add('cgt')
        elif node.op == BinOp.LT:
            if node.arg1.node_type == TypeDesc.STR:
                self.add(
                    f'call {MSIL_TYPE_NAMES[BaseType.INT]} class {RUNTIME_CLASS_NAME}::compare({MSIL_TYPE_NAMES[BaseType.STR]}, {MSIL_TYPE_NAMES[BaseType.STR]})')
                self.add('ldc.i4.0')
                self.add('clt')
            else:
                self.add('clt')
        elif node.op == BinOp.GE:
            if node.arg1.node_type == TypeDesc.STR:
                self.add(
                    f'call {MSIL_TYPE_NAMES[BaseType.INT]} class {RUNTIME_CLASS_NAME}::compare({MSIL_TYPE_NAMES[BaseType.STR]}, {MSIL_TYPE_NAMES[BaseType.STR]})')
                self.add('ldc.i4', '-1')
                self.add('cgt')
            else:
                self.add('clt')
                self.add('ldc.i4.0')
                self.add('ceq')
        elif node.op == BinOp.LE:
            if node.arg1.node_type == TypeDesc.STR:
                self.add(
                    f'call {MSIL_TYPE_NAMES[BaseType.INT]} class {RUNTIME_CLASS_NAME}::compare({MSIL_TYPE_NAMES[BaseType.STR]}, {MSIL_TYPE_NAMES[BaseType.STR]})')
                self.add('ldc.i4.1')
                self.add('clt')
            else:
                self.add('cgt')
                self.add('ldc.i4.0')
                self.add('ceq')
        elif node.op == BinOp.ADD:
            if node.arg1.node_type == TypeDesc.STR:
                self.add(
                    f'call {MSIL_TYPE_NAMES[BaseType.STR]} class {RUNTIME_CLASS_NAME}::concat({MSIL_TYPE_NAMES[BaseType.STR]}, {MSIL_TYPE_NAMES[BaseType.STR]})')
            else:
                self.add('add')
        elif node.op == BinOp.SUB:
            self.add('sub')
        elif node.op == BinOp.MUL:
            self.add('mul')
        elif node.op == BinOp.DIV:
            self.add('div')
        elif node.op == BinOp.MOD:
            self.add('rem')
        elif node.op == BinOp.LOGICAL_AND:
            self.add('and')
        elif node.op == BinOp.LOGICAL_OR:
            self.add('or')
        elif node.op == BinOp.BIT_AND:
            self.add('and')
        elif node.op == BinOp.BIT_OR:
            self.add('or')
        else:
            pass

    @visitor.when(TypeConvertNode)
    def msil_gen(self, node: TypeConvertNode) -> None:
        self.msil_gen(node.expr)
        # часто встречаемые варианты будет реализовывать в коде, а не через класс Runtime
        if node.node_type.base_type == BaseType.FLOAT and node.expr.node_type.base_type == BaseType.INT:
            self.add('conv.r8')
        elif node.node_type.base_type == BaseType.BOOL and node.expr.node_type.base_type == BaseType.INT:
            self.add('ldc.i4.0')
            self.add('ceq')
            self.add('ldc.i4.0')
            self.add('ceq')
        else:
            cmd = f'call {MSIL_TYPE_NAMES[node.node_type.base_type]} class {RUNTIME_CLASS_NAME}::convert({MSIL_TYPE_NAMES[node.expr.node_type.base_type]})'
            self.add(cmd)

    @visitor.when(CallNode)
    def msil_gen(self, node: CallNode) -> None:
        for param in node.params:
            self.msil_gen(param)
        class_name = RUNTIME_CLASS_NAME if node.func.node_ident.built_in else PROGRAM_CLASS_NAME
        param_types = ', '.join(MSIL_TYPE_NAMES[param.node_type.base_type] for param in node.params)
        cmd = f'call {MSIL_TYPE_NAMES[node.node_type.base_type]} class {class_name}::{node.func.name}({param_types})'
        self.add(cmd)

    @visitor.when(ReturnNode)
    def msil_gen(self, node: ReturnNode) -> None:
        self.msil_gen(node.val)
        self.add('ret')

    @visitor.when(IfNode)
    def msil_gen(self, node: IfNode) -> None:
        else_label = CodeLabel()
        end_label = CodeLabel()

        self.msil_gen(node.cond)
        self.add('brfalse', else_label)
        self.msil_gen(node.then_stmt)
        self.add('br', end_label)
        self.add('', label=else_label)
        if node.else_stmt:
            self.msil_gen(node.else_stmt)
        self.add('', label=end_label)

        # @visitor.when(IfNode)
        # def msil_gen(self, node: IfNode) -> None:
        #     else_label = CodeLabel()
        #     end_label = CodeLabel()
        #     self.msil_gen(node.cond)
        #     self.add('brfalse', else_label)
        #     self.msil_gen(node.then_stmt)
        #     self.add('br', end_label)
        #     self.add('', label=else_label)
        #     if node.else_stmt:
        #         self.msil_gen(node.else_stmt)
        #     self.add('', label=end_label)

    @visitor.when(WhileNode)
    def msil_gen(self, node: WhileNode) -> None:
        start_label = CodeLabel()
        end_label = CodeLabel()
        self.add('', label=start_label)
        self.msil_gen(node.cond)
        end_label = CodeLabel()
        self.add('brfalse', end_label)
        self.msil_gen(node.body)
        self.add('br', start_label)
        self.add('', label=end_label)

    @visitor.when(ForNode)
    def msil_gen(self, node: ForNode) -> None:
        start_label = CodeLabel()
        end_label = CodeLabel()
        self.msil_gen(node.init)
        self.add('', label=start_label)
        self.msil_gen(node.cond)
        self.add('brfalse', end_label)
        self.msil_gen(node.body)
        # self.msil_gen(node.step)
        self.add('br', start_label)
        self.add('', label=end_label)

    @visitor.when(FuncNode)
    def msil_gen(self, func: FuncNode) -> None:
        params = ''
        for p in func.params:
            if len(params) > 0:
                params += ', '
            params += f'{MSIL_TYPE_NAMES[p.type.type.base_type]} {str(p.name.name)}'
        self.add(f'.method public static {MSIL_TYPE_NAMES[func.type.type.base_type]} {func.name}({params}) cil managed')
        self.add('{')

        local_vars_decls = find_vars_decls(func)
        decl = '.locals init ('
        count = 0
        for node in local_vars_decls:
            if node.ident.node_ident.scope in (ScopeType.LOCAL,):
                if count > 0:
                    decl += ', '
                msil_type = get_msil_type(node.type.name)
                decl += f'{msil_type} _v{node.ident.node_ident.index}'
                count += 1
        decl += ')'
        if count > 0:
            self.add(decl)
        self.msil_gen(func.body)

    @visitor.when(StmtListNode)
    def msil_gen(self, node: StmtListNode) -> None:
        for stmt in node.exprs:
            self.msil_gen(stmt)

    def msil_gen_program(self, prog: StmtListNode):
        self.start()
        global_vars_decls = find_vars_decls(prog)
        for node in global_vars_decls:
            if node.ident.node_ident.scope in (ScopeType.GLOBAL, ScopeType.GLOBAL_LOCAL):
                msil_type = get_msil_type(node.type.name)
                self.add(f'.field public static {msil_type} _gv{node.ident.node_ident.index}')
        for stmt in prog.exprs:
            if isinstance(stmt, FuncNode):
                self.msil_gen(stmt)
        self.add('')
        self.add('.method public static void Main()')
        self.add('{')
        self.add('.entrypoint')
        for stmt in prog.childs:
            if not isinstance(stmt, FuncNode):
                self.msil_gen(stmt)

        # т.к. "глобальный" код будет функцией, обязательно надо добавить ret
        self.add('ret')

        self.add('}')
        self.end()
