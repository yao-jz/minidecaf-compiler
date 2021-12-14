import random
import copy
from backend.dataflow.basicblock import BasicBlock, BlockKind
from backend.dataflow.cfg import CFG
from backend.dataflow.loc import Loc
from backend.reg.regalloc import RegAlloc
from backend.riscv.riscvasmemitter import RiscvAsmEmitter, RiscvSubroutineEmitter
from backend.subroutineemitter import SubroutineEmitter
from backend.subroutineinfo import SubroutineInfo
from utils.riscv import Riscv
from utils.tac.holeinstr import HoleInstr
from utils.tac.reg import Reg
from utils.tac.temp import Temp

import sys
"""
BruteRegAlloc: one kind of RegAlloc

bindings: map from temp.index to Reg

we don't need to take care of GlobalTemp here
because we can remove all the GlobalTemp in selectInstr process

1. accept：根据每个函数的 CFG 进行寄存器分配，寄存器分配结束后生成相应汇编代码
2. bind：将一个 Temp 与寄存器绑定
3. unbind：将一个 Temp 与相应寄存器解绑定
4. localAlloc：根据数据流对一个 BasicBlock 内的指令进行寄存器分配
5. allocForLoc：每一条指令进行寄存器分配
6. allocRegFor：根据数据流决定为当前 Temp 分配哪一个寄存器
"""

class BruteRegAlloc(RegAlloc):
    def __init__(self, emitter: RiscvAsmEmitter) -> None:
        super().__init__(emitter)
        self.bindings = {}
        self.parameter_temp = []
        self.globalTemp = []
        for reg in emitter.allocatableRegs:
            reg.used = False

    def accept(self, graph: CFG, info: SubroutineInfo, numArgs = 0, sp_offset=0) -> None:
        
        subEmitter = self.emitter.emitSubroutine(info, numArgs, sp_offset)

        can_be_visited = [0]
        for bb in graph.iterator():
            if(not bb.id in can_be_visited):
                continue
            for vis in graph.links[bb.id][1]:
                can_be_visited.append(vis)
            # you need to think more here
            # maybe we don't need to alloc regs for all the basic blocks
            # print("alloc for function: ", info.funcLabel.name)
            if bb.label is not None:
                subEmitter.emitLabel(bb.label)
            self.localAlloc(bb, subEmitter)

        subEmitter.emitEnd()

    def bind(self, temp: Temp, reg: Reg):
        reg.used = True
        self.bindings[temp.index] = reg
        reg.occupied = True
        reg.temp = temp

    def unbind(self, temp: Temp):
        if temp.index in self.bindings:
            self.bindings[temp.index].occupied = False
            self.bindings.pop(temp.index)

    def localAlloc(self, bb: BasicBlock, subEmitter: SubroutineEmitter):
        self.bindings.clear()
        for reg in self.emitter.allocatableRegs:
            reg.occupied = False
        # in step9, you may need to think about how to store callersave regs here
        for loc in bb.allSeq():
            subEmitter.emitComment(str(loc.instr))
            if (type(loc.instr) == Riscv.SPAdd):
                temp_sp_offset = abs(loc.instr.offset)
                subEmitter.now_sp_offset += temp_sp_offset
                for i in subEmitter.offsets.keys():
                    subEmitter.offsets[i] += temp_sp_offset
            self.allocForLoc(loc, subEmitter)

        for tempindex in bb.liveOut:
            if tempindex in self.bindings:
                subEmitter.emitStoreToStack(self.bindings.get(tempindex))

        if (not bb.isEmpty()) and (bb.kind is not BlockKind.CONTINUOUS):
            self.allocForLoc(bb.locs[len(bb.locs) - 1], subEmitter)

    def allocForLoc(self, loc: Loc, subEmitter: SubroutineEmitter):
        # print("Begin")
        instr = loc.instr
        srcRegs: list[Reg] = []
        dstRegs: list[Reg] = []
        for i in range(len(instr.srcs)):
            temp = instr.srcs[i]
            if isinstance(temp, Reg):
                srcRegs.append(temp)
            else:
                srcRegs.append(self.allocRegFor(temp, True, loc.liveIn, subEmitter))

        for i in range(len(instr.dsts)):
            temp = instr.dsts[i]
            if isinstance(temp, Reg):
                dstRegs.append(temp)
            else:
                dstRegs.append(self.allocRegFor(temp, False, loc.liveIn, subEmitter))

        if(type(loc.instr) == Riscv.Param):
            return

        if(type(loc.instr) == Riscv.ParamDecl):
            subEmitter.addParaRegs(dstRegs[0])
            return
        elif(type(loc.instr) == Riscv.CallAssignment):
            self.storeRegtoStack(loc, subEmitter, srcRegs)

        # temp = None
        if(type(loc.instr) == Riscv.Load):
            self.globalTemp.append({"temp": loc.instr.dst, "offset": loc.instr.offset, "dst": dstRegs[0], "src": srcRegs[0], "symbol": loc.instr.symbol})

        # if(type(loc.instr) == Riscv.Move):
        #     temp = copy.deepcopy(loc.instr.dst)
            # print(loc.instr, temp)

        subEmitter.emitNative(instr.toNative(dstRegs, srcRegs))
        # if(type(loc.instr) == Riscv.Move):
        #     print("here", temp)
        #     for k in self.globalTemp:
        #         print(k)
        #         if(temp == k["temp"]):
        #             subEmitter.emitNative(
        #                 Riscv.NativeStoreWord(Riscv.T0, Riscv.SP, 8)
        #             )
        #             subEmitter.emitNative(
        #                 Riscv.NativeLoadAddr(Riscv.T0, k["symbol"])
        #             )
        #             subEmitter.emitNative(
        #                 Riscv.NativeStoreWord(k["dst"], k["src"], k["offset"])
        #             )
        #             subEmitter.emitNative(
        #                 Riscv.NativeLoadWord(Riscv.T0, Riscv.SP, 8)
        #             )
        #             self.globalTemp.remove(k)
            

        if(type(loc.instr) == Riscv.CallAssignment):
            self.loadRegfromStack(loc, subEmitter)
        # print("end")


    def storeRegtoStack(self, loc, subEmitter, regs):
        numArgs = len(loc.instr.paratemp)
        subEmitter.emitNative(Riscv.SPAdd(-(len(Riscv.CallerSaved) * 4 + 8 + 4 * numArgs)))
        for i in range(len(Riscv.CallerSaved)):
            if Riscv.CallerSaved[i].isUsed():
                subEmitter.emitNative(
                    Riscv.NativeStoreWord(Riscv.CallerSaved[i], Riscv.SP, 8 + 4 * numArgs + i * 4)
                )
        # if Riscv.RA.isUsed():
        subEmitter.emitNative(
            Riscv.NativeStoreWord(Riscv.RA, Riscv.SP, 4 * numArgs)
        )
        # if Riscv.FP.isUsed():
        subEmitter.emitNative(
            Riscv.NativeStoreWord(Riscv.FP, Riscv.SP, 4 * numArgs + 4)
        )
        for i in range(numArgs):
            subEmitter.emitNative(
                Riscv.NativeStoreWord(regs[i], Riscv.SP, i * 4)
            )

        
    
    def loadRegfromStack(self, loc, subEmitter):
        numArgs = len(loc.instr.paratemp)
        
        for i in range(len(Riscv.CallerSaved)):
            if Riscv.CallerSaved[i].isUsed():
                subEmitter.emitNative(
                    Riscv.NativeLoadWord(Riscv.CallerSaved[i], Riscv.SP, 8 + 4 * numArgs + i * 4)
                )
        # if Riscv.RA.isUsed():
        subEmitter.emitNative(
            Riscv.NativeLoadWord(Riscv.RA, Riscv.SP, 4 * numArgs)
        )
        # if Riscv.FP.isUsed():
        subEmitter.emitNative(
            Riscv.NativeLoadWord(Riscv.FP, Riscv.SP, 4 * numArgs + 4)
        )
        subEmitter.emitNative(Riscv.SPAdd(len(Riscv.CallerSaved) * 4 + 8 + 4 * numArgs))


    def allocRegFor(
        self, temp: Temp, isRead: bool, live: set[int], subEmitter: SubroutineEmitter
    ):
        if temp.index in self.bindings:
            return self.bindings[temp.index]
        # for i in self.emitter.allocatableRegs:
        #     print(i.name, i.occupied, end=" ")
        # print("")
        for reg in self.emitter.allocatableRegs:
            if (not reg.occupied) or (not reg.temp.index in live):
                subEmitter.emitComment(
                    "  allocate {} to {}  (read: {}):".format(
                        str(temp), str(reg), str(isRead)
                    )
                )
                if isRead:
                    subEmitter.emitLoadFromStack(reg, temp)
                if reg.occupied:
                    self.unbind(reg.temp)
                self.bind(temp, reg)
                return reg

        reg = self.emitter.allocatableRegs[
            random.randint(0, len(self.emitter.allocatableRegs))
        ]
        subEmitter.emitStoreToStack(reg)
        subEmitter.emitComment("  spill {} ({})".format(str(reg), str(reg.temp)))
        self.unbind(reg.temp)
        self.bind(temp, reg)
        subEmitter.emitComment(
            "  allocate {} to {} (read: {})".format(str(temp), str(reg), str(isRead))
        )
        if isRead:
            subEmitter.emitLoadFromStack(reg, temp)
        return reg
