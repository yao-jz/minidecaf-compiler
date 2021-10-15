from typing import Sequence, Tuple

from backend.asmemitter import AsmEmitter
# from frontend.ast.node import T
from utils.error import IllegalArgumentException
from utils.label.label import Label, LabelKind
from utils.riscv import Riscv
from utils.tac.reg import Reg
from utils.tac.tacfunc import TACFunc
from utils.tac.tacinstr import *
from utils.tac.tacvisitor import TACVisitor

from ..subroutineemitter import SubroutineEmitter
from ..subroutineinfo import SubroutineInfo
import sys

"""
RiscvAsmEmitter: an AsmEmitter for RiscV
"""


class RiscvAsmEmitter(AsmEmitter):
    def __init__(
        self,
        allocatableRegs: list[Reg],
        callerSaveRegs: list[Reg],
        golbalVars: list = None
    ) -> None:
        super().__init__(allocatableRegs, callerSaveRegs)
        self.globalVars = golbalVars
        bssVars = []
        dataVars = []
        for decl in self.globalVars:
            if(decl.init_expr.name == "NULL"):
                bssVars.append(decl)
            else:
                dataVars.append(decl)
        # the start of the asm code
        # int step10, you need to add the declaration of global var here
        if(len(bssVars) > 0):
            self.printer.println(".bss")
            for d in bssVars:
                self.printer.println(".global " + str(d.ident.value))
                self.printer.println(d.ident.value + ":")
                self.printer.println("    " + ".space 4")
        if(len(dataVars)> 0):
            self.printer.println(".data")
            for d in dataVars:
                self.printer.println(".global " + d.ident.value)
                self.printer.println(d.ident.value + ":")
                self.printer.println("    " + ".word " + str(d.init_expr.value))
        self.printer.println(".text")
        self.printer.println(".global main")
        self.printer.println("")
        
        


    # transform tac instrs to RiscV instrs
    # collect some info which is saved in SubroutineInfo for SubroutineEmitter
    def selectInstr(self, func: TACFunc) -> tuple[list[str], SubroutineInfo]:
        selector: RiscvAsmEmitter.RiscvInstrSelector = (
            RiscvAsmEmitter.RiscvInstrSelector(func.entry)
        )

        for instr in func.getInstrSeq():
            # print(instr)
            instr.accept(selector)
        info = SubroutineInfo(func.entry)
        # sys.exit(0)
        return (selector.seq, info)

    # use info to construct a RiscvSubroutineEmitter
    def emitSubroutine(self, info: SubroutineInfo, numArgs: int):
        return RiscvSubroutineEmitter(self, info, numArgs)

    # return all the string stored in asmcodeprinter
    def emitEnd(self):
        return self.printer.close()

    class RiscvInstrSelector(TACVisitor):
        def __init__(self, entry: Label) -> None:
            self.entry = entry
            self.seq = []
            self.paratemp = []  # 记录下次函数调用的temp，函数调用后清空

        # in step11, you need to think about how to deal with globalTemp in almost all the visit functions. 
        def visitReturn(self, instr: Return) -> None:
            if instr.value is not None:
                self.seq.append(Riscv.Move(Riscv.A0, instr.value))
            else:
                self.seq.append(Riscv.LoadImm(Riscv.A0, 0))
            self.seq.append(Riscv.JumpToEpilogue(self.entry))

        def visitMark(self, instr: Mark) -> None:
            self.seq.append(Riscv.RiscvLabel(instr.label))

        def visitLoadImm4(self, instr: LoadImm4) -> None:
            self.seq.append(Riscv.LoadImm(instr.dst, instr.value))

        def visitUnary(self, instr: Unary) -> None:
            self.seq.append(Riscv.Unary(instr.op, instr.dst, instr.operand))
 
        def visitBinary(self, instr: Binary) -> None:
            self.seq.append(Riscv.Binary(instr.op, instr.dst, instr.lhs, instr.rhs))

        def visitCondBranch(self, instr: CondBranch) -> None:
            self.seq.append(Riscv.Branch(instr.cond, instr.label))
        
        def visitBranch(self, instr: Branch) -> None:
            self.seq.append(Riscv.Jump(instr.target))

        def visitAssign(self, instr: Assign) -> None:

            self.seq.append(Riscv.Move(instr.dst, instr.src))

        def visitCallAssignment(self, instr: CallAssignment) -> None:
            self.seq.append(Riscv.CallAssignment(instr.dst, instr.target, self.paratemp))
            self.seq.append(Riscv.Move(instr.dst, Riscv.A0))
            self.paratemp = []
            
        def visitParam(self, instr: Param) -> None:
            self.paratemp.append(instr.src)
            self.seq.append(Riscv.Param(instr.src))

        def visitParamDecl(self, instr: ParamDecl) -> None:
            self.seq.append(Riscv.ParamDecl(instr.dst))

        def visitLoad(self, instr: Load) -> None:
            self.seq.append(Riscv.Load(instr.dst, instr.src, instr.offset, instr.symbol))

        def visitLoadSymbol(self, instr: LoadSymbol) -> None:
            self.seq.append(Riscv.LoadSymbol(instr.dst, instr.symbol))

        # in step9, you need to think about how to pass the parameters and how to store and restore callerSave regs
        # in step11, you need to think about how to store the array 
"""
RiscvAsmEmitter: an SubroutineEmitter for RiscV
"""

class RiscvSubroutineEmitter(SubroutineEmitter):
    def __init__(self, emitter: RiscvAsmEmitter, info: SubroutineInfo, numArgs: int) -> None:
        super().__init__(emitter, info)
        
        self.numArgs = numArgs
        # + 8 is for the RA reg and BP reg and 4 * numArgs is for parameters
        self.nextLocalOffset = 4 * len(Riscv.CalleeSaved) + 8 + 4 * numArgs
        
        # the buf which stored all the NativeInstrs in this function
        self.buf: list[NativeInstr] = []

        # from temp to int
        # record where a temp is stored in the stack
        self.offsets = {}
        self.paraReg = []

        self.printer.printLabel(info.funcLabel)
       
        # in step9, step11 you can compute the offset of local array and parameters here

    def addParaRegs(self, reg: Reg):
        self.paraReg.append(reg)

    def emitComment(self, comment: str) -> None:
        # you can add some log here to help you debug
        # print(comment)
        pass
    
    # store some temp to stack
    # usually happen when reaching the end of a basicblock
    # in step9, you need to think about the function parameters here
    def emitStoreToStack(self, src: Reg) -> None:
        if src.temp.index not in self.offsets:
            self.offsets[src.temp.index] = self.nextLocalOffset
            self.nextLocalOffset += 4
        self.buf.append(
            Riscv.NativeStoreWord(src, Riscv.SP, self.offsets[src.temp.index])
        )

    # load some temp from stack
    # usually happen when using a temp which is stored to stack before
    # in step9, you need to think about the fuction parameters here
    def emitLoadFromStack(self, dst: Reg, src: Temp):
        # print(self.offsets)
        if src.index not in self.offsets:
            raise IllegalArgumentException()
        else:
            self.buf.append(
                Riscv.NativeLoadWord(dst, Riscv.SP, self.offsets[src.index])
            )

    # add a NativeInstr to buf
    # when calling the fuction emitEnd, all the instr in buf will be transformed to RiscV code
    def emitNative(self, instr: NativeInstr):
        self.buf.append(instr)

    def emitLabel(self, label: Label):
        self.buf.append(Riscv.RiscvLabel(label).toNative([], []))

    
    def emitEnd(self):
        self.printer.printComment("start of prologue")
        self.printer.printInstr(Riscv.SPAdd(-self.nextLocalOffset))

        # in step9, you need to think about how to store RA here
        # you can get some ideas from how to save CalleeSaved regs
        for i in range(len(Riscv.CalleeSaved)):
            if Riscv.CalleeSaved[i].isUsed():
                self.printer.printInstr(
                    Riscv.NativeStoreWord(Riscv.CalleeSaved[i], Riscv.SP, 4 * i)
                )
        # save RA and FP
        # TODO: calculate offset for RA and FP
        # if Riscv.RA.isUsed():
        self.printer.printInstr(
            Riscv.NativeStoreWord(Riscv.RA, Riscv.SP, 4 * len(Riscv.CalleeSaved))
        )
        # if Riscv.FP.isUsed():
        self.printer.printInstr(
            Riscv.NativeStoreWord(Riscv.FP, Riscv.SP, 4 * len(Riscv.CalleeSaved) + 4)
        )

        # if(self.numArgs > 0):


        self.printer.printComment("end of prologue")
        self.printer.println("")

        self.printer.printComment("start of body")

        # in step9, you need to think about how to pass the parameters here
        # you can use the stack or regs (use stack)
        # TODO: pass the parameters
        for index in range(len(self.paraReg)):
            self.printer.printInstr(
                Riscv.NativeLoadWord(self.paraReg[index], Riscv.SP, self.nextLocalOffset + index * 4)
            )

        # using asmcodeprinter to output the RiscV code
        for instr in self.buf:
            self.printer.printInstr(instr)

        self.printer.printComment("end of body")
        self.printer.println("")

        self.printer.printLabel(
            Label(LabelKind.TEMP, self.info.funcLabel.name + Riscv.EPILOGUE_SUFFIX)
        )
        self.printer.printComment("start of epilogue")

        for i in range(len(Riscv.CalleeSaved)):
            if Riscv.CalleeSaved[i].isUsed():
                self.printer.printInstr(
                    Riscv.NativeLoadWord(Riscv.CalleeSaved[i], Riscv.SP, 4 * i)
                )
        # if Riscv.RA.isUsed():
        self.printer.printInstr(
                Riscv.NativeLoadWord(Riscv.RA, Riscv.SP, 4 * len(Riscv.CalleeSaved))
            )
        # if Riscv.FP.isUsed():
        self.printer.printInstr(
                Riscv.NativeLoadWord(Riscv.FP, Riscv.SP, 4 * len(Riscv.CalleeSaved) + 4)
            )

        self.printer.printInstr(Riscv.SPAdd(self.nextLocalOffset))
        self.printer.printComment("end of epilogue")
        self.printer.println("")

        self.printer.printInstr(Riscv.NativeReturn())
        self.printer.println("")
