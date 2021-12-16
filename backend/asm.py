from backend.dataflow.cfg import CFG
from backend.dataflow.cfgbuilder import CFGBuilder
from backend.dataflow.livenessanalyzer import LivenessAnalyzer
from backend.reg.bruteregalloc import BruteRegAlloc
from backend.riscv.riscvasmemitter import RiscvAsmEmitter
from utils.tac.tacprog import TACProg
import sys

"""
Asm: we use it to generate all the asm code for the program
"""

class Asm:
    def __init__(self, emitter: RiscvAsmEmitter, regAlloc: BruteRegAlloc) -> None:
        self.emitter = emitter
        self.regAlloc = regAlloc

    def transform(self, prog: TACProg):
        analyzer = LivenessAnalyzer()
        new_funcs = []
        func_list = []
        # for func in prog.funcs:
        #     new_funcs.append(func)
        # for func in new_funcs:
        for func in prog.funcs:
            func_list.append(func.entry.name)
            # print(type(func))
            ## 尝试先弄main函数
            # if(func.entry.name != "main"):
            #     continue
            pair = self.emitter.selectInstr(func)
            builder = CFGBuilder(func_list)
            cfg: CFG = builder.buildFrom(pair[0])
            analyzer.accept(cfg)
            self.regAlloc.accept(cfg, pair[1], func.numArgs, pair[2])
        # for func in prog.funcs:
        #     # 然后弄其他函数
        #     if(func.entry.name == "main"):
        #         continue
        #     pair = self.emitter.selectInstr(func)
        #     builder = CFGBuilder()
        #     cfg: CFG = builder.buildFrom(pair[0])
        #     analyzer.accept(cfg)
        #     self.regAlloc.accept(cfg, pair[1])
        return self.emitter.emitEnd()
