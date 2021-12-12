from typing import Protocol, TypeVar, cast

from frontend.ast.node import Node, NullType
from frontend.ast.tree import *
from frontend.ast.visitor import RecursiveVisitor, Visitor
from frontend.scope.globalscope import GlobalScope
from frontend.scope.scope import Scope, ScopeKind
from frontend.scope.scopestack import ScopeStack
from frontend.symbol.funcsymbol import FuncSymbol
from frontend.symbol.symbol import Symbol
from frontend.symbol.varsymbol import VarSymbol
from frontend.type.array import ArrayType
from frontend.type.type import DecafType
from utils.error import *
from utils.riscv import MAX_INT
from utils.tac.tacinstr import Assign
import sys

"""
The namer phase: resolve all symbols defined in the abstract syntax tree and store them in symbol tables (i.e. scopes).
"""


class Namer(Visitor[ScopeStack, None]):
    def __init__(self) -> None:
        pass

    # Entry of this phase
    def transform(self, program: Program) -> Program:
        # Global scope. You don't have to consider it until Step 9.
        program.globalScope = GlobalScope
        ctx = ScopeStack(program.globalScope)

        program.accept(self, ctx)

        return program

    def visitProgram(self, program: Program, ctx: ScopeStack) -> None:
        # Check if the 'main' function is missing
        if not program.hasMainFunc():
            raise DecafNoMainFuncError
        for child in program:
            child.accept(self, ctx)
        

    def visitFunction(self, func: Function, ctx: ScopeStack) -> None:
        ok = ctx.findConflict(func.ident.value)
        if(not ok):
            new_symbol = FuncSymbol(func.ident.value, func.ret_t.type, ctx.currentScope())
            if func.parameters is not None:
                for child in func.parameters:
                    new_symbol.addParaType(child.var_t.type)
            func.setattr("symbol", new_symbol)
            ctx.declare(new_symbol)
            func.body.accept(self, ctx, func.parameters)
        else:
            raise DecafDeclConflictError()

    def visitParameter(self, para: Parameter, ctx: ScopeStack) -> None:
        for child in para:
            child.accept(self, ctx)

    def visitPostfix(self, postfix: Postfix, ctx: ScopeStack) -> None:
        func = ctx.lookup(postfix.ident.value)
        if(func is None):   # no function identifier found
            raise DecafBadFuncCallError()
        # check the num and type of parameters
        if postfix.exprList.getNumChildren() == len(func.para_type):
            pass    # TODO: check the type of the parameters
        else:
            raise DecafBadFuncCallError()
        
        postfix.ident.accept(self, ctx)
        postfix.exprList.accept(self, ctx)

    def visitExpressionList(self, exprList: ExpressionList, ctx: ScopeStack) -> None:
        for child in exprList:
            child.accept(self, ctx)
    
    def visitBlock(self, block: Block, ctx: ScopeStack, para: Parameter = None) -> None:
        block_scope = Scope(ScopeKind.LOCAL)
        ctx.open(block_scope)
        if para is not None:
            for child in para:
                child.accept(self, ctx)
        for child in block:
            child.accept(self, ctx)
        ctx.close()

    def visitReturn(self, stmt: Return, ctx: ScopeStack) -> None:
        stmt.expr.accept(self, ctx)

    def visitFor(self, stmt: For, ctx: ScopeStack) -> None:
        """
        1. Open a local scope for stmt.init.
        2. Visit stmt.init, stmt.cond, stmt.update.
        3. Open a loop in ctx (for validity checking of break/continue)
        4. Visit body of the loop.
        5. Close the loop and the local scope.
        """
        init_scope = Scope(ScopeKind.LOCAL)
        ctx.open(init_scope)
        if(stmt.init is not None):
            stmt.init.accept(self, ctx)
        if(stmt.cond is not None):
            stmt.cond.accept(self, ctx)
        if(stmt.update is not None):
            stmt.update.accept(self, ctx)
        ctx.openLoop()
        stmt.body.accept(self, ctx)
        ctx.closeLoop()
        ctx.close()

    def visitIf(self, stmt: If, ctx: ScopeStack) -> None:
        stmt.cond.accept(self, ctx)
        stmt.then.accept(self, ctx)

        # check if the else branch exists
        if not stmt.otherwise is NULL:
            stmt.otherwise.accept(self, ctx)

    def visitWhile(self, stmt: While, ctx: ScopeStack) -> None:
        # scope
        stmt.cond.accept(self, ctx)
        ctx.openLoop()
        stmt.body.accept(self, ctx)
        ctx.closeLoop()


    def visitDoWhile(self, stmt: DoWhile, ctx: ScopeStack) -> None:
        """
        1. Open a loop in ctx (for validity checking of break/continue)
        2. Visit body of the loop.
        3. Close the loop.
        4. Visit the condition of the loop.
        """
        ctx.openLoop()
        stmt.body.accept(self, ctx)
        ctx.closeLoop()
        stmt.cond.accept(self, ctx)

    def visitBreak(self, stmt: Break, ctx: ScopeStack) -> None:
        if not ctx.inLoop():
            raise DecafBreakOutsideLoopError()

    def visitContinue(self, stmt: Continue, ctx: ScopeStack) -> None:
        """
        1. Refer to the implementation of visitBreak.
        """
        if not ctx.inLoop():
            raise DecafContinueOutsideLoopError()

    def visitDeclaration(self, decl: Declaration, ctx: ScopeStack) -> None:
        """
        1. Use ctx.findConflict to find if a variable with the same name has been declared.
        2. If not, build a new VarSymbol, and put it into the current scope using ctx.declare.
        3. Set the 'symbol' attribute of decl.
        4. If there is an initial value, visit it.
        """
        ok = ctx.findConflict(decl.ident.value)
        if(not ok):
            # if(type(decl.var_t.type) == ArrayType):
            #     print(type(decl.var_t.type)._indexes)
            new_symbol = VarSymbol(decl.ident.value, decl.var_t.type)
            decl.setattr("symbol", new_symbol)
            ctx.declare(new_symbol)
            if(decl.init_expr):
                decl.init_expr.accept(self, ctx)
        else:
            raise DecafDeclConflictError()
    
    def visitIndexExpr(self, indexexpr: IndexExpr, ctx: ScopeStack) -> None:
        symbol = ctx.lookup(indexexpr.base.value)

        for index in indexexpr.index:
            if(index.value < 0):
                raise DecafBadArraySizeError()
        if(symbol.type != INT and symbol.type.dim != len(indexexpr.index)):
            raise DecafTypeMismatchError()
        if(symbol is not None):
            indexexpr.setattr("symbol", symbol)
        else:
            raise DecafUndefinedVarError()
        

        

    def visitAssignment(self, expr: Assignment, ctx: ScopeStack) -> None:
        """
        1. Refer to the implementation of visitBinary.
        """
        expr.lhs.accept(self, ctx)
        expr.rhs.accept(self, ctx)

    def visitUnary(self, expr: Unary, ctx: ScopeStack) -> None:
        expr.operand.accept(self, ctx)

    def visitBinary(self, expr: Binary, ctx: ScopeStack) -> None:
        print(expr)
        expr.lhs.accept(self, ctx)
        expr.rhs.accept(self, ctx)

    def visitCondExpr(self, expr: ConditionExpression, ctx: ScopeStack) -> None:
        """
        1. Refer to the implementation of visitBinary.
        """
        expr.cond.accept(self, ctx)
        expr.then.accept(self, ctx)
        expr.otherwise.accept(self, ctx)

    def visitIdentifier(self, ident: Identifier, ctx: ScopeStack) -> None:
        """
        1. Use ctx.lookup to find the symbol corresponding to ident.
        2. If it has not been declared, raise a DecafUndefinedVarError.
        3. Set the 'symbol' attribute of ident.
        """
        symbol = ctx.lookup(ident.value)
        if(symbol is not None):
            ident.setattr("symbol", symbol)
        else:
            raise DecafUndefinedVarError()

    def visitIntLiteral(self, expr: IntLiteral, ctx: ScopeStack) -> None:
        value = expr.value
        if value > MAX_INT:
            raise DecafBadIntValueError(value)
