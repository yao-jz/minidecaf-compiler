import sys
from backend.dataflow.basicblock import BasicBlock
from backend.dataflow.cfg import CFG
from utils.tac.temp import Temp

from utils.riscv import Riscv
"""
LivenessAnalyzer: do the liveness analysis according to the CFG
"""


class LivenessAnalyzer:
    def __init__(self) -> None:
        pass

    def accept(self, graph: CFG):
        for bb in graph.nodes:
            self.computeDefAndLiveUseFor(bb)
            bb.liveIn = set()
            bb.liveIn.update(bb.liveUse)
            bb.liveOut = set()

        changed = True
        while changed:
            changed = False
            for bb in graph.nodes:
                for next in graph.getSucc(bb.id):
                    bb.liveOut.update(graph.getBlock(next).liveIn)

                liveOut = bb.liveOut.copy()
                for v in bb.define:
                    liveOut.discard(v)

                before = len(bb.liveIn)
                bb.liveIn.update(liveOut)
                after = len(bb.liveIn)

                if before != after:
                    changed = True
        
        # for bb in graph.nodes:
            # if bb.id == 8:
            #     print(bb.define)
            #     print(bb.liveUse)
            #     print(bb.liveIn)
            #     print(bb.liveOut)
            #     sys.exit(0)

        for bb in graph.nodes:
            self.analyzeLivenessForEachLocIn(bb)
        # for bb in graph.nodes:
        #     if bb.id == 8:
        #         print(bb.define)
        #         print(bb.liveUse)
        #         print(bb.liveIn)
        #         print(bb.liveOut)
        #         for loc in bb.allSeq():
        #             print(loc.instr)
        #             print(loc.liveIn)
        #             print(loc.liveOut)
        #         sys.exit(0)
        # sys.exit(0)

    def computeDefAndLiveUseFor(self, bb: BasicBlock):
        bb.define = set()
        bb.liveUse = set()
        for loc in bb.iterator():
            for read in loc.instr.getRead():
                if not read in bb.define:
                    bb.liveUse.add(read)
            bb.define.update(loc.instr.getWritten())

    def analyzeLivenessForEachLocIn(self, bb: BasicBlock):
        #print("this is reverse loc of ", bb.id)
        liveOut = bb.liveOut.copy()
        for loc in bb.backwardIterator():
            loc.liveOut = liveOut.copy()
            #print("processing ", loc.instr)
            #print("liveOut = ", liveOut)
            #print("getWritten: ", loc.instr.getWritten())
            for v in loc.instr.getWritten():
                # print(v)
                liveOut.discard(v)
            #print(loc.instr.getRead())
            liveOut.update(loc.instr.getRead())
            loc.liveIn = liveOut.copy()
            # if type(loc.instr) == Riscv.Move:
            #     print("loc.livein = ", loc.liveIn)
            #     print("loc.liveOut = ", loc.liveOut)
