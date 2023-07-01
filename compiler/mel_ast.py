from abc import ABC, abstractmethod
from contextlib import suppress
from typing import Optional, Union, Tuple, Callable

from .semantic import TYPE_CONVERTIBILITY, BIN_OP_TYPE_COMPATIBILITY, BinOp, SinOp, \
    TypeDesc, IdentDesc, ScopeType, IdentScope, SemanticException


class AstNode(ABC):
    """Базовый абстрактый класс узла AST-дерева
    """

    init_action: Callable[['AstNode'], None] = None

    def __init__(self, row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__()
        self.row = row
        self.col = col
        for k, v in props.items():
            setattr(self, k, v)
        if AstNode.init_action is not None:
            AstNode.init_action(self)
        self.node_type: Optional[TypeDesc] = None
        self.node_ident: Optional[IdentDesc] = None

    @abstractmethod
    def __str__(self) -> str:
        pass

    @property
    def childs(self) -> Tuple['AstNode', ...]:
        return ()

    def to_str(self):
        return str(self)

    def to_str_full(self):
        r = ''
        if self.node_ident:
            r = str(self.node_ident)
        elif self.node_type:
            r = str(self.node_type)
        return self.to_str() + (' : ' + r if r else '')

    def semantic_error(self, message: str):
        raise SemanticException(message, self.row, self.col)

    def semantic_check(self, scope: IdentScope) -> None:
        pass

    @property
    def tree(self) -> [str, ...]:
        r = [self.to_str_full()]
        childs = self.childs
        for i, child in enumerate(childs):
            ch0, ch = '├', '│'
            if i == len(childs) - 1:
                ch0, ch = '└', ' '
            r.extend(((ch0 if j == 0 else ch) + ' ' + s for j, s in enumerate(child.tree)))
        return tuple(r)

    def visit(self, func: Callable[['AstNode'], None]) -> None:  # кусочек реализации паттерна посетитель
        func(self)
        map(func, self.childs)  # посещаем все поддерева

    def __getitem__(self, index):
        return self.childs[index] if index < len(self.childs) else None


class _GroupNode(AstNode):
    """Класс для группировки других узлов (вспомогательный, в синтаксисе нет соотвествия)
    """

    def __init__(self, name: str, *childs: AstNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.name = name
        self._childs = childs

    def __str__(self) -> str:
        return self.name

    @property
    def childs(self) -> Tuple['AstNode', ...]:
        return self._childs


class ExprNode(AstNode, ABC):
    """Абстракный класс для выражений в AST-дереве
    """

    pass


class LiteralNode(ExprNode):
    """Класс для представления в AST-дереве литералов (числа, строки, логическое значение)
    """

    def __init__(self, literal: str,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.literal = literal
        if literal in ('true', 'false'):
            self.value = bool(literal)
        else:
            self.value = eval(literal)

    def __str__(self) -> str:
        return self.literal

    def semantic_check(self, scope: IdentScope) -> None:
        if isinstance(self.value, bool):
            self.node_type = TypeDesc.BOOL
        # проверка должна быть позже bool, т.к. bool наследник от int
        elif isinstance(self.value, int):
            self.node_type = TypeDesc.INT
        elif isinstance(self.value, float):
            self.node_type = TypeDesc.FLOAT
        elif isinstance(self.value, str):
            self.node_type = TypeDesc.STR
        else:
            self.semantic_error('Неизвестный тип {} для {}'.format(type(self.value), self.value))


class IdentNode(ExprNode):
    """Класс для представления в AST-дереве идентификаторов
    """

    def __init__(self, name: str,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.name = str(name)

    def __str__(self) -> str:
        return str(self.name)

    def semantic_check(self, scope: IdentScope) -> None:
        ident = scope.get_ident(self.name)
        if ident is None:
            self.semantic_error('Идентификатор {} не найден'.format(self.name))
        self.node_type = ident.type
        self.node_ident = ident


class TypeNode(IdentNode):
    """Класс для представления в AST-дереве типов данный
       (при появлении составных типов данных должен быть расширен)
    """

    def __init__(self, name: str, generic=None,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(name, row=row, col=col, **props)
        self.generic = generic
        self.type = None
        with suppress(SemanticException):
            self.type = TypeDesc.from_str(name)

    def to_str_full(self):
        return self.to_str()

    @property
    def childs(self):
        return (self.generic, ) if self.generic else []

    def semantic_check(self, scope: IdentScope) -> None:
        if self.type is None:
            self.semantic_error('Неизвестный тип {}'.format(self.name))


class SinOpNode(ExprNode):
    """Класс для представления в AST-дереве бинарных операций
    """

    def __init__(self, op: SinOp, arg: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.op = op
        self.arg = arg

    def __str__(self) -> str:
        return str(self.op.value)

    @property
    def childs(self) -> Tuple[ExprNode]:
        return self.arg,


class SeqNode(ExprNode):
    """Класс для представления в AST-дереве бинарных операций
    """

    def __init__(self, startArg: ExprNode, seqOp: str, endArg: ExprNode,
                 stepArg: ExprNode = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.startArg = startArg
        self.seqOp = seqOp
        self.endArg = endArg
        self.stepArg = stepArg

    def __str__(self) -> str:
        return 'seq'

    @property
    def childs(self) -> Tuple[ExprNode, ExprNode]:
        return [self.startArg, self.seqOp, self.endArg] + [self.stepArg] if self.stepArg is not None else []


class BinOpNode(ExprNode):
    """Класс для представления в AST-дереве бинарных операций
    """

    def __init__(self, op: BinOp, arg1: ExprNode, arg2: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self) -> str:
        return str(self.op.value)

    @property
    def childs(self) -> Tuple[ExprNode, ExprNode]:
        return self.arg1, self.arg2

    def semantic_check(self, scope: IdentScope) -> None:
        self.arg1.semantic_check(scope)
        self.arg2.semantic_check(scope)

        if self.arg1.node_type.is_simple or self.arg2.node_type.is_simple:
            compatibility = BIN_OP_TYPE_COMPATIBILITY[self.op]
            args_types = (self.arg1.node_type.base_type, self.arg2.node_type.base_type)
            if args_types in compatibility:
                self.node_type = TypeDesc.from_base_type(compatibility[args_types])
                return

            if self.arg2.node_type.base_type in TYPE_CONVERTIBILITY:
                for arg2_type in TYPE_CONVERTIBILITY[self.arg2.node_type.base_type]:
                    args_types = (self.arg1.node_type.base_type, arg2_type)
                    if args_types in compatibility:
                        self.arg2 = type_convert(self.arg2, TypeDesc.from_base_type(arg2_type))
                        self.node_type = TypeDesc.from_base_type(compatibility[args_types])
                        return
            if self.arg1.node_type.base_type in TYPE_CONVERTIBILITY:
                for arg1_type in TYPE_CONVERTIBILITY[self.arg1.node_type.base_type]:
                    args_types = (arg1_type, self.arg2.node_type.base_type)
                    if args_types in compatibility:
                        self.arg1 = type_convert(self.arg1, TypeDesc.from_base_type(arg1_type))
                        self.node_type = TypeDesc.from_base_type(compatibility[args_types])
                        return

        self.semantic_error("Оператор {} не применим к типам ({}, {})".format(
            self.op, self.arg1.node_type, self.arg2.node_type
        ))


class CallNode(ExprNode):
    """Класс для представления в AST-дереве вызова функций
       (в языке программирования может быть как expression, так и statement)
    """

    def __init__(self, func: IdentNode, *params: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.func = func
        self.params = params

    def __str__(self) -> str:
        return 'call'

    @property
    def childs(self) -> Tuple[IdentNode, ...]:
        return (self.func, *self.params)

    def semantic_check(self, scope: IdentScope) -> None:
        func = scope.get_ident(self.func.name)
        if func is None:
            self.semantic_error('Функция {} не найдена'.format(self.func.name))
        if not func.type.func:
            self.semantic_error('Идентификатор {} не является функцией'.format(func.name))
        if len(func.type.params) != len(self.params):
            self.semantic_error('Кол-во аргументов {} не совпадает (ожидалось {}, передано {})'.format(
                func.name, len(func.type.params), len(self.params)
            ))
        params = []
        error = False
        decl_params_str = fact_params_str = ''
        for i in range(len(self.params)):
            param: ExprNode = self.params[i]
            param.semantic_check(scope)
            if (len(decl_params_str) > 0):
                decl_params_str += ', '
            decl_params_str += str(func.type.params[i])
            if (len(fact_params_str) > 0):
                fact_params_str += ', '
            fact_params_str += str(param.node_type)
            try:
                params.append(type_convert(param, func.type.params[i]))
            except:
                error = True
        if error:
            self.semantic_error('Фактические типы ({1}) аргументов функции {0} не совпадают с формальными ({2})\
                                    и не приводимы'.format(
                func.name, fact_params_str, decl_params_str
            ))
        else:
            self.params = tuple(params)
            self.func.node_type = func.type
            self.func.node_ident = func
            self.node_type = func.type.return_type


class TypeConvertNode(ExprNode):
    """Класс для представления в AST-дереве операций конвертации типов данных
       (в языке программирования может быть как expression, так и statement)
    """

    def __init__(self, expr: ExprNode, type_: TypeDesc,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.expr = expr
        self.type = type_
        self.node_type = type_

    def __str__(self) -> str:
        return 'convert'

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return (_GroupNode(str(self.type), self.expr), )


def type_convert(expr: ExprNode, type_: TypeDesc, except_node: Optional[AstNode] = None, comment: Optional[str] = None) -> ExprNode:
    """Метод преобразования ExprNode узла AST-дерева к другому типу
    :param expr: узел AST-дерева
    :param type_: требуемый тип
    :param except_node: узел, о которого будет исключение
    :param comment: комментарий
    :return: узел AST-дерева c операцией преобразования
    """

    if expr.node_type is None:
        except_node.semantic_error('Тип выражения не определен')
    if type_ is None:
        except_node.node_type = expr.node_type
        except_node.type = TypeNode(except_node.node_type.base_type)
        return expr
    if expr.node_type == type_:
        return expr
    if expr.node_type.is_simple and type_.is_simple and \
            expr.node_type.base_type in TYPE_CONVERTIBILITY and type_.base_type in TYPE_CONVERTIBILITY[expr.node_type.base_type]:
        return TypeConvertNode(expr, type_)
    else:
        (except_node if except_node else expr).semantic_error('Тип {0}{2} не конвертируется в {1}'.format(
            expr.node_type, type_, ' ({})'.format(comment) if comment else ''
        ))


class StmtNode(ExprNode, ABC):
    """Абстракный класс для деклараций или инструкций в AST-дереве
    """

    def to_str_full(self):
        return self.to_str()


class StmtListNode(StmtNode):
    """Класс для представления в AST-дереве последовательности инструкций
    """

    def __init__(self, *exprs: StmtNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.exprs = exprs
        self.program = False

    def __str__(self) -> str:
        return '...'

    @property
    def childs(self) -> Tuple[StmtNode, ...]:
        return self.exprs

    def semantic_check(self, scope: IdentScope) -> None:
        if not self.program:
            scope = IdentScope(scope)
        for expr in self.exprs:
            expr.semantic_check(scope)
        self.node_type = TypeDesc.VOID


class AssignNode(ExprNode):
    """Класс для представления в AST-дереве оператора присваивания
    """

    def __init__(self, var: IdentNode, val: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.var = var
        self.val = val

    def __str__(self) -> str:
        return '='

    @property
    def childs(self) -> Tuple[IdentNode, ExprNode]:
        return self.var, self.val

    def semantic_check(self, scope: IdentScope) -> None:
        self.var.semantic_check(scope)
        self.val.semantic_check(scope)
        self.val = type_convert(self.val, self.var.node_type, self, 'присваиваемое значение')
        self.node_type = self.var.node_type


class VarsNode(StmtNode):
    """Класс для представления в AST-дереве объявления переменнных
    """

    def __init__(self, type_: TypeNode, *vars_: Union[IdentNode, 'AssignNode'],
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.type = type_
        self.vars = vars_

    def __str__(self) -> str:
        return str(self.type)

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return self.vars

    def semantic_check(self, scope: IdentScope) -> None:
        self.type.semantic_check(scope)
        for var in self.vars:
            var_node: IdentNode = var.var if isinstance(var, AssignNode) else var
            try:
                scope.add_ident(IdentDesc(var_node.name, self.type.type))
            except SemanticException as e:
                var_node.semantic_error(e.message)
            var.semantic_check(scope)
        self.node_type = TypeDesc.VOID


class VarNode(StmtNode):
    """Класс для представления в AST-дереве объявления переменнных
    """

    def __init__(self, *params,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.declare = params[0]
        params = params[1:]
        sep = params[1]
        self.ident = params[0]
        self.type = None
        self.var = None
        if isinstance(sep, str):
            self.type = params[2]
            if len(params) > 3:
                self.var = params[3]
        else:
            self.var = params[1]

    def __str__(self) -> str:
        return self.declare

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        childs = []
        if self.type is not None:
            childs.append(self.type)
        childs.append(self.ident)
        if self.var is not None:
            childs.append(self.var)
        return childs

    def semantic_check(self, scope: IdentScope) -> None:
        if self.type is not None:
            self.type.semantic_check(scope)
        self.var.semantic_check(scope)
        var = self.ident
        var_node: IdentNode = var if isinstance(var, AssignNode) else var
        self.var = type_convert(self.var, self.type.type if self.type is not None else None, self, 'присваиваемое значение')
        try:
            scope.add_ident(IdentDesc(var_node.name, self.type.type))
        except SemanticException as e:
            var_node.semantic_error(e.message)
        var.semantic_check(scope)
        self.node_type = TypeDesc.VOID


class ReturnNode(StmtNode):
    """Класс для представления в AST-дереве оператора return
    """

    def __init__(self, val: ExprNode = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.val = val

    def __str__(self) -> str:
        return 'return'

    @property
    def childs(self) -> Tuple[ExprNode]:
        return (self.val, ) if self.val is not None else ()

    def semantic_check(self, scope: IdentScope) -> None:
        self.val.semantic_check(IdentScope(scope))
        func = scope.curr_func
        if func is None:
            self.semantic_error('Оператор return применим только к функции')
        self.val = type_convert(self.val, func.func.type.return_type, self, 'возвращаемое значение')
        self.node_type = TypeDesc.VOID


class IfNode(StmtNode):
    """Класс для представления в AST-дереве условного оператора
    """

    def __init__(self, cond: ExprNode, then_stmt: StmtNode, else_stmt: Optional[StmtNode] = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.cond = cond
        self.then_stmt = then_stmt
        self.else_stmt = else_stmt

    def __str__(self) -> str:
        return 'if'

    @property
    def childs(self) -> Tuple[ExprNode, StmtNode, Optional[StmtNode]]:
        return (self.cond, self.then_stmt, *((self.else_stmt,) if self.else_stmt else tuple()))

    def semantic_check(self, scope: IdentScope) -> None:
        self.cond.semantic_check(scope)
        self.cond = type_convert(self.cond, TypeDesc.BOOL, None, 'условие')
        self.then_stmt.semantic_check(IdentScope(scope))
        if self.else_stmt:
            self.else_stmt.semantic_check(IdentScope(scope))
        self.node_type = TypeDesc.VOID


class ForNode(StmtNode):
    """Класс для представления в AST-дереве цикла for
    """

    def __init__(self, init: IdentNode, cond: ExprNode, body: StmtNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.init = init
        self.cond = cond
        self.body = body

    def __str__(self) -> str:
        return 'for'

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return self.init, self.cond, self.body

    def semantic_check(self, scope: IdentScope) -> None:
        scope = IdentScope(scope)
        self.init.semantic_check(scope)
        if self.cond == EMPTY_STMT:
            self.cond = LiteralNode('true')
        self.cond.semantic_check(scope)
        self.cond = type_convert(self.cond, TypeDesc.BOOL, None, 'условие')
        self.body.semantic_check(IdentScope(scope))
        self.node_type = TypeDesc.VOID


class WhileNode(StmtNode):
    """Класс для представления в AST-дереве условного оператора
    """

    def __init__(self, cond: ExprNode, body: Optional[StmtNode],
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.cond = cond
        self.body = body

    def __str__(self) -> str:
        return 'while'

    @property
    def childs(self) -> Tuple[ExprNode, StmtNode, Optional[StmtNode]]:
        return self.cond, self.body

    def semantic_check(self, scope: IdentScope):
        self.cond.semantic_check(scope)
        self.cond = type_convert(self.cond, TypeDesc.BOOL, None, 'условие')
        self.body.semantic_check(IdentScope(scope))
        self.node_type = TypeDesc.VOID


class DoWhileNode(StmtNode):
    """Класс для представления в AST-дереве цикла while
    """

    def __init__(self, body: StmtNode, condition: ExprNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.condition = condition
        self.body = body

    def __str__(self) -> str:
        return 'do while'

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return self.condition, self.body



class ParamNode(StmtNode):
    """Класс для представления в AST-дереве объявления параметра функции
    """

    def __init__(self, name: IdentNode, type_: TypeNode, expr: ExprNode = None,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.type = type_
        self.name = name
        self.value = expr

    def __str__(self) -> str:
        return str(self.type)

    @property
    def childs(self) -> Tuple[IdentNode]:
        childs = [self.name]
        if self.value is not None:
            childs.append(self.value)
        return childs

    def semantic_check(self, scope: IdentScope) -> None:
        self.type.semantic_check(scope)
        self.name.node_type = self.type.type
        try:
            self.name.node_ident = scope.add_ident(IdentDesc(self.name.name, self.type.type, ScopeType.PARAM))
        except SemanticException:
            raise self.name.semantic_error('Параметр {} уже объявлен'.format(self.name.name))
        self.node_type = TypeDesc.VOID


class FuncNode(StmtNode):
    """Класс для представления в AST-дереве объявления функции
    """

    def __init__(self, type_: TypeNode, name: IdentNode, params: Tuple[ParamNode], body: StmtNode,
                 row: Optional[int] = None, col: Optional[int] = None, **props) -> None:
        super().__init__(row=row, col=col, **props)
        self.type = type_ if type_ is not None else TypeNode('Void')
        self.name = name
        self.params = params
        self.body = body

    def __str__(self) -> str:
        return 'function'

    @property
    def childs(self) -> Tuple[AstNode, ...]:
        return _GroupNode(str(self.type), self.name), _GroupNode('params', *self.params), self.body

    def semantic_check(self, scope: IdentScope) -> None:
        if scope.curr_func:
            self.semantic_error("Объявление функции ({}) внутри другой функции не поддерживается".format(self.name.name))
        parent_scope = scope
        self.type.semantic_check(scope)
        scope = IdentScope(scope)

        # временно хоть какое-то значение, чтобы при добавлении параметров находить scope функции
        scope.func = EMPTY_IDENT
        params = []
        for param in self.params:
            # при проверке параметров происходит их добавление в scope
            param.semantic_check(scope)
            params.append(param.type.type)

        type_ = TypeDesc(None, self.type.type, tuple(params))
        func_ident = IdentDesc(self.name.name, type_)
        scope.func = func_ident
        self.name.node_type = type_
        try:
            self.name.node_ident = parent_scope.curr_global.add_ident(func_ident)
        except SemanticException as e:
            self.name.semantic_error("Повторное объявление функции {}".format(self.name.name))
        self.body.semantic_check(scope)
        self.node_type = TypeDesc.VOID

EMPTY_STMT = StmtListNode()
EMPTY_IDENT = IdentDesc('', TypeDesc.VOID)