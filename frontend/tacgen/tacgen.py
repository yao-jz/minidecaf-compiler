import copy
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
import sys
"""
The TAC generation phase: translate the abstract syntax tree into three-address code.
"""
def get_index(t):
    index = []
    while True:
        index.append(t.length)
        t = t.base
        if t == INT:
            break
    return index

def get_offset(array_type, index_list):
    type_index_list = []
    while True:
        type_index_list.append(array_type.length)
        array_type = array_type.base
        if array_type == INT:
            break
    offset = 0
    for i in range(len(index_list)):
        temp = i + 1
        temp_result = 1
        while temp < len(index_list):
            temp_result *= type_index_list[temp]
            temp += 1
        offset += temp_result * index_list[i].value
    offset *= 4
    return offset

class TACGen(Visitor[FuncVisitor, None]):
    def __init__(self) -> None:
        self.program = None
        self.pw = None
        self.handle_func = []

    # Entry of this phase
    def transform(self, program: Program) -> TACProg:
        self.program = program
        funcs = program.functions()
        decls = program.globals()
        self.pw = ProgramWriter([k for k in funcs.keys()])
        for globalName in decls.keys():
            decl = decls[globalName]
            self.pw.globalVars.append(decl)
            # print(decl.var_t, decl.ident.value, type(decl.init_expr))
            # if(type(decl.init_expr)== NullType):
            #     self.pw.globalVars.append()
            # elif(type(decl.init_expr)==IntLiteral):
            #     pass
            # else:
            #     print(type(decl.init_expr))
            #     print("[debug] step into else")
        mainFunc = program.mainFunc()
        # The function visitor of 'main' is special.
        mv = self.pw.visitMainFunc()

        mainFunc.body.accept(self, mv)
        # Remember to call mv.visitEnd after the translation a function.
        mv.visitEnd()
        return self.pw.visitEnd()



    def visitPostfix(self, postfix: Postfix, mv: FuncVisitor) -> None:
        if postfix.isArray is False:
            for child in postfix.exprList:
                child.accept(self, mv)
                mv.visitParam(child.getattr("val"))
            temp_list = [child.getattr("val") for child in postfix.exprList.children]
            func_list = self.program.functions()
            thisFunc = func_list[postfix.ident.value]
            if not thisFunc.ident.value in self.handle_func:
                self.handle_func.append(thisFunc.ident.value)
                
                if not hasattr(thisFunc.parameters, "children"):
                    fv = self.pw.visitFunc(postfix.ident.value, 0)
                else:
                    fv = self.pw.visitFunc(postfix.ident.value, len(thisFunc.parameters.children))
                # now_temp = 0
                if thisFunc.parameters is not None:
                    for child in thisFunc.parameters:
                        child_symbol = child.getattr("symbol")
                        child_symbol.temp = fv.freshTemp()
                        child.setattr("symbol", child_symbol)
                        # now_temp += 1
                # fv.nextTempId = now_temp
                if thisFunc.parameters is not None:
                    for child in thisFunc.parameters:
                        fv.visitParamDecl(child.getattr("symbol").temp)
                thisFunc.body.accept(self, fv)
                fv.visitEnd()
                mv.nextTempId = fv.nextTempId
            postfix.setattr("val", mv.visitCallAssignment(postfix.ident.value))
        else:
            for decl in self.pw.globalVars:
                if decl.ident.value == postfix.ident.value:
                    addrTemp = mv.freshTemp()
                    loadTemp = mv.freshTemp()
                    mv.visitLoadSymbol(addrTemp, postfix.ident.value)
                    mv.visitLoadTemp(loadTemp, addrTemp, 0, postfix.ident.value)
                    new_symbol = postfix.ident.getattr("symbol")
                    new_symbol.temp = loadTemp
                    postfix.ident.setattr("symbol", new_symbol)
            for child in postfix.exprList:
                child.accept(self, mv)
            temp_list = [child.getattr("val") for child in postfix.exprList.children]
            offset = mv.visitLoad(0)
            index_list = get_index(postfix.arrayType)
            mul_list = []
            for i in range(1, len(index_list)):
                tempresult = 1
                for j in range(i, len(index_list)):
                    tempresult *= index_list[j]
                mul_list.append(mv.visitLoad(tempresult))
            mul_list.append(mv.visitLoad(1))
            for i in range(len(temp_list)):
                mv.visitAssignment(
                    offset, 
                    mv.visitBinary(
                        tacop.BinaryOp.ADD, 
                        offset, 
                        mv.visitBinary(
                            tacop.BinaryOp.MUL,
                            temp_list[i],
                            mul_list[i]
                        )
                    )
                )
            loadTemp = mv.freshTemp()
            addrTemp = mv.freshTemp()
            mv.visitAssignment(addrTemp, mv.visitBinary(tacop.BinaryOp.ADD, offset, postfix.ident.getattr("symbol").temp))
            mv.visitLoadTemp(loadTemp, addrTemp, 0, postfix.ident.value)
            new_symbol = copy.deepcopy(postfix.ident.getattr("symbol"))
            new_symbol.temp = loadTemp
            postfix.setattr("offset", offset)
            postfix.setattr("val", new_symbol.temp)
            postfix.setattr("symbol", new_symbol)



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
        for decl in self.pw.globalVars:
            if(decl.ident.value == ident.value):
                addrTemp = mv.freshTemp()
                loadTemp = mv.freshTemp()
                mv.visitLoadSymbol(addrTemp, ident.value)
                mv.visitLoadTemp(loadTemp, addrTemp, 0, ident.value)
                new_symbol = ident.getattr("symbol")
                new_symbol.temp = loadTemp
                ident.setattr("symbol", new_symbol)

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
            if(type(decl.var_t) == TArray):
                symbol.temp = mv.visitAlloc(decl.var_t.type.size)
            else:
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
        elif(type(decl.init_expr) == Binary):
            decl.init_expr.accept(self, mv)
            symbol.temp = mv.freshTemp()
            decl.setattr("symbol", symbol)
            mv.visitAssignment(symbol.temp, decl.init_expr.getattr("val"))
        elif(type(decl.init_expr) == Postfix):
            decl.init_expr.accept(self, mv)
            symbol.temp = mv.freshTemp()
            decl.setattr("symbol", symbol)
            mv.visitAssignment(symbol.temp, decl.init_expr.getattr("val"))
        else:
            print(type(decl.init_expr))
            print("[debug] step into else")
            raise ValueError("")
        



    def visitAssignment(self, expr: Assignment, mv: FuncVisitor) -> None:
        """
        1. Visit the right hand side of expr, and get the temp variable of left hand side.
        2. Use mv.visitAssignment to emit an assignment instruction.
        3. Set the 'val' attribute of expr as the value of assignment instruction.
        """
        expr.rhs.accept(self, mv)
        if type(expr.lhs) == Identifier:
            if(hasattr(expr.lhs.getattr("symbol"),"temp")):
                left_temp = expr.lhs.getattr("symbol").temp
            else:
                symbol = expr.lhs.getattr("symbol")
                symbol.temp = mv.freshTemp()
                expr.lhs.setattr("symbol", symbol)
                left_temp = expr.lhs.getattr("symbol").temp
            expr.lhs.accept(self, mv)
            expr.setattr("val", mv.visitAssignment(left_temp, expr.rhs.getattr("val")))
        elif type(expr.lhs) == Postfix:
            expr.lhs.accept(self, mv)
            left_temp = expr.lhs.ident.getattr("symbol").temp
            addrTemp = mv.freshTemp()
            mv.visitAssignment(addrTemp, mv.visitBinary(tacop.BinaryOp.ADD, expr.lhs.getattr("offset"), left_temp))
            expr.setattr("val", mv.visitStore(addrTemp, expr.rhs.getattr("val"), 0, expr.lhs.ident.value))
        

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
        # print(op, expr.lhs.getattr("val"), expr.rhs.getattr("val"))
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
