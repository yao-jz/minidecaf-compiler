import utils.riscv as riscv
from frontend.ast import node
from frontend.ast.tree import *
from frontend.ast.visitor import Visitor
from frontend.ast.node import NullType
from frontend.symbol.varsymbol import VarSymbol
from frontend.type.array import ArrayType
from utils.tac import tacop
from utils.tac.funcvisitor import FuncVisitor
from utils.tac.programwriter import ProgramWriter
from utils.tac.tacprog import TACProg
from utils.tac.temp import Temp

"""
The TAC generation phase: translate the abstract syntax tree into three-address code.
"""


class TACGen(Visitor[FuncVisitor, None]):
    def __init__(self) -> None:
        self.program = None
        self.pw = None

    # Entry of this phase
    def transform(self, program: Program) -> TACProg:
        self.program = program
        funcs = program.functions()
        self.pw = ProgramWriter([k for k in funcs.keys()])
        mainFunc = program.mainFunc()
        # The function visitor of 'main' is special.
        mv = self.pw.visitMainFunc()

        mainFunc.body.accept(self, mv)
        # Remember to call mv.visitEnd after the translation a function.
        mv.visitEnd()
        # for k in funcs.keys():
        #     if k == "main":
        #         continue
        #     else:
        #         thisFunc = funcs[k]
        #         fv = pw.visitFunc(k, len(thisFunc.parameters.children))
        #         thisFunc.body.accept(self, fv)
        #         fv.visitEnd()
        # Remember to call pw.visitEnd before finishing the translation phase.
        return self.pw.visitEnd()


    def visitPostfix(self, postfix: Postfix, mv: FuncVisitor) -> None:
        for child in postfix.exprList:
            child.accept(self, mv)
            mv.visitParam(child.getattr("val"))
        temp_list = [child.getattr("val") for child in postfix.exprList.children]
        func_list = self.program.functions()
        thisFunc = func_list[postfix.ident.value]
        now_temp = 0
        for child in thisFunc.parameters:
            child_symbol = child.getattr("symbol")
            child_symbol.temp = temp_list[now_temp]
            child.setattr("symbol", child_symbol)
            now_temp += 1
        fv = self.pw.visitFunc(postfix.ident.value, len(thisFunc.parameters.children))
        fv.nextTempId = now_temp
        thisFunc.body.accept(self, fv)
        fv.visitEnd()
        mv.nextTempId = fv.nextTempId
        postfix.setattr("val", mv.visitCallAssignment(postfix.ident.value))

    def visitExpressionList(self, exprList: ExpressionList, mv: FuncVisitor) -> None:
        for child in exprList:
            child.accept(self, mv)


    def visitBlock(self, block: Block, mv: FuncVisitor, para: Parameter = None) -> None:
        for child in block:
            child.accept(self, mv)

    def visitReturn(self, stmt: Return, mv: FuncVisitor) -> None:
        stmt.expr.accept(self, mv)
        mv.visitReturn(stmt.expr.getattr("val"))

    def visitBreak(self, stmt: Break, mv: FuncVisitor) -> None:
        mv.visitBranch(mv.getBreakLabel())

    def visitContinue(self, stmt: Continue, mv: FuncVisitor) -> None:
        mv.visitBranch(mv.getContinueLabel())

    def visitIdentifier(self, ident: Identifier, mv: FuncVisitor) -> None:
        """
        1. Set the 'val' attribute of ident as the temp variable of the 'symbol' attribute of ident.
        """
        ident.setattr("val", ident.getattr("symbol").temp)

    def visitDeclaration(self, decl: Declaration, mv: FuncVisitor) -> None:
        """
        1. Get the 'symbol' attribute of decl.
        2. Use mv.freshTemp to get a new temp variable for this symbol.
        3. If the declaration has an initial value, use mv.visitAssignment to set it.
        """
        symbol = decl.getattr("symbol")
        if(type(decl.init_expr) == IntLiteral):
            another_temp = mv.visitLoad(decl.init_expr.value)
            symbol.temp = mv.freshTemp()
            decl.setattr("symbol", symbol)
            mv.visitAssignment(symbol.temp, another_temp)
        elif(type(decl.init_expr) == Identifier):
            decl.init_expr.accept(self, mv)
            symbol.temp = mv.freshTemp()
            decl.setattr("symbol", symbol)
            mv.visitAssignment(symbol.temp, decl.init_expr.getattr("val"))
        elif(type(decl.init_expr) == NullType):
            symbol.temp = mv.visitLoad(0)
            decl.setattr("symbol", symbol)
        elif(type(decl.init_expr) == Assignment):
            decl.init_expr.accept(self, mv)
            symbol.temp = mv.freshTemp()
            decl.setattr("symbol", symbol)
            mv.visitAssignment(symbol.temp, decl.init_expr.getattr("val"))
        elif(type(decl.init_expr) == ConditionExpression):
            decl.init_expr.accept(self, mv)
            symbol.temp = mv.freshTemp()
            decl.setattr("symbol", symbol)
            mv.visitAssignment(symbol.temp, decl.init_expr.getattr("val"))
        else:
            print(type(decl.init_expr))
            print("[debug] step into else")
        



    def visitAssignment(self, expr: Assignment, mv: FuncVisitor) -> None:
        """
        1. Visit the right hand side of expr, and get the temp variable of left hand side.
        2. Use mv.visitAssignment to emit an assignment instruction.
        3. Set the 'val' attribute of expr as the value of assignment instruction.
        """
        expr.rhs.accept(self, mv)
        if(hasattr(expr.lhs.getattr("symbol"),"temp")):
            left_temp = expr.lhs.getattr("symbol").temp
        else:
            symbol = expr.lhs.getattr("symbol")
            symbol.temp = mv.freshTemp()
            expr.lhs.setattr("symbol", symbol)
            left_temp = expr.lhs.getattr("symbol").temp
        expr.setattr("val", mv.visitAssignment(left_temp, expr.rhs.getattr("val")))

    def visitIf(self, stmt: If, mv: FuncVisitor) -> None:
        stmt.cond.accept(self, mv)

        if stmt.otherwise is NULL:
            skipLabel = mv.freshLabel()
            mv.visitCondBranch(
                tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), skipLabel
            )
            stmt.then.accept(self, mv)
            mv.visitLabel(skipLabel)
        else:
            skipLabel = mv.freshLabel()
            exitLabel = mv.freshLabel()
            mv.visitCondBranch(
                tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), skipLabel
            )
            stmt.then.accept(self, mv)
            mv.visitBranch(exitLabel)
            mv.visitLabel(skipLabel)
            stmt.otherwise.accept(self, mv)
            mv.visitLabel(exitLabel)

    def visitFor(self, stmt: For, mv: FuncVisitor) -> None:
        beginLabel = mv.freshLabel()
        loopLabel = mv.freshLabel()
        breakLabel = mv.freshLabel()
        mv.openLoop(breakLabel, loopLabel)

        if(stmt.init is not None):
            stmt.init.accept(self, mv)
        mv.visitLabel(beginLabel)
        if(stmt.cond is not None):
            stmt.cond.accept(self, mv)
            mv.visitCondBranch(tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), breakLabel)
        stmt.body.accept(self, mv)

        mv.visitLabel(loopLabel)
        if(stmt.update is not None):
            stmt.update.accept(self, mv)
        mv.visitBranch(beginLabel)
        mv.visitLabel(breakLabel)
        mv.closeLoop()

    def visitDoWhile(self, stmt: DoWhile, mv: FuncVisitor) -> None:
        beginLabel = mv.freshLabel()
        loopLabel = mv.freshLabel()
        breakLabel = mv.freshLabel()
        mv.openLoop(breakLabel, loopLabel)


        mv.visitLabel(beginLabel)
        stmt.body.accept(self, mv)

        mv.visitLabel(loopLabel)
        stmt.cond.accept(self, mv)
        mv.visitCondBranch(tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), breakLabel)
        mv.visitBranch(beginLabel)

        mv.visitLabel(breakLabel)
        mv.closeLoop()

    def visitWhile(self, stmt: While, mv: FuncVisitor) -> None:
        beginLabel = mv.freshLabel()
        loopLabel = mv.freshLabel()
        breakLabel = mv.freshLabel()
        mv.openLoop(breakLabel, loopLabel)

        mv.visitLabel(beginLabel)
        stmt.cond.accept(self, mv)
        mv.visitCondBranch(tacop.CondBranchOp.BEQ, stmt.cond.getattr("val"), breakLabel)

        stmt.body.accept(self, mv)
        mv.visitLabel(loopLabel)
        mv.visitBranch(beginLabel)
        mv.visitLabel(breakLabel)
        mv.closeLoop()

    def visitUnary(self, expr: Unary, mv: FuncVisitor) -> None:
        expr.operand.accept(self, mv)

        op = {
            node.UnaryOp.Neg: tacop.UnaryOp.NEG,
            node.UnaryOp.Not: tacop.UnaryOp.NOT,
            node.UnaryOp.LogicNot: tacop.UnaryOp.SEQZ
            # You can add unary operations here.
        }[expr.op]
        expr.setattr("val", mv.visitUnary(op, expr.operand.getattr("val")))

    def visitBinary(self, expr: Binary, mv: FuncVisitor) -> None:
        expr.lhs.accept(self, mv)
        expr.rhs.accept(self, mv)

        op = {
            node.BinaryOp.Add: tacop.BinaryOp.ADD,
            node.BinaryOp.Sub: tacop.BinaryOp.SUB,
            node.BinaryOp.Mul: tacop.BinaryOp.MUL,
            node.BinaryOp.Div: tacop.BinaryOp.DIV,
            node.BinaryOp.Mod: tacop.BinaryOp.REM,
            node.BinaryOp.EQ: tacop.BinaryOp.EQU,
            node.BinaryOp.NE: tacop.BinaryOp.NEQ,
            node.BinaryOp.LT: tacop.BinaryOp.SLT,
            node.BinaryOp.GT: tacop.BinaryOp.SGT,
            node.BinaryOp.LE: tacop.BinaryOp.LEQ,
            node.BinaryOp.GE: tacop.BinaryOp.GEQ,
            node.BinaryOp.LogicOr: tacop.BinaryOp.LOR,
            node.BinaryOp.LogicAnd: tacop.BinaryOp.LAND,
            # You can add binary operations here.
        }[expr.op]
        expr.setattr(
            "val", mv.visitBinary(op, expr.lhs.getattr("val"), expr.rhs.getattr("val"))
        )

    def visitCondExpr(self, expr: ConditionExpression, mv: FuncVisitor) -> None:
        """
        1. Refer to the implementation of visitIf and visitBinary.
        """
        expr.cond.accept(self, mv)
        expr_temp = mv.freshTemp()
        skipLabel = mv.freshLabel()
        exitLabel = mv.freshLabel()
        mv.visitCondBranch(
            tacop.CondBranchOp.BEQ, expr.cond.getattr("val"), skipLabel
        )
        expr.then.accept(self, mv)
        mv.visitAssignment(expr_temp, expr.then.getattr("val"))
        mv.visitBranch(exitLabel)   # jump
        mv.visitLabel(skipLabel)
        expr.otherwise.accept(self, mv)
        mv.visitAssignment(expr_temp, expr.otherwise.getattr("val"))
        mv.visitLabel(exitLabel)    # end
        
        expr.setattr(
            "val", expr_temp
        )

        
        

    def visitIntLiteral(self, expr: IntLiteral, mv: FuncVisitor) -> None:
        expr.setattr("val", mv.visitLoad(expr.value))
