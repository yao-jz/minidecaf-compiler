FUNCTION<main>:
    _T0 = 0
    _T1 = _T0
_L1:
    _T2 = 3
    _T3 = (_T1 < _T2)
    BEQZ _T3 _L3
    _T4 = LOAD_SYMBOL state
    _T5 = LOAD _T4, 0
    _T6 = 1
    _T7 = (_T5 * _T6)
    _T8 = 1531011
    _T9 = (_T7 + _T8)
    _T10 = 32768
    _T11 = (_T9 % _T10)
    _T5 = _T11
    _T12 = LOAD_SYMBOL a
    _T14 = 0
    _T15 = 4
    _T16 = (_T1 * _T15)
    _T17 = (_T14 + _T16)
    _T14 = _T17
    _T20 = (_T14 + _T12)
    _T19 = _T20
    _T18 = LOAD _T19, 0
    _T22 = (_T14 + _T12)
    _T21 = _T22
    STORE _T21, _T11, 0
_L2:
    _T23 = 1
    _T24 = (_T1 + _T23)
    _T1 = _T24
    JUMP _L1
_L3:
    _T25 = LOAD_SYMBOL a
    _T27 = 1
    _T28 = 0
    _T29 = 4
    _T30 = (_T27 * _T29)
    _T31 = (_T28 + _T30)
    _T28 = _T31
    _T34 = (_T28 + _T25)
    _T33 = _T34
    _T32 = LOAD _T33, 0
    return _T32

   .bss
    .global a
    a:
        .space 2000
    .data
    .global state
    state:
        .word 1
    .text
    .global main
    
main:
    # start of prologue
    addi sp, sp, -56
    sw ra, 44(sp)
    sw fp, 48(sp)
    # end of prologue
    
    # start of body
    li t0, 0
    mv t1, t0
    sw t1, 52(sp)
_L1:
    li t0, 3
    lw t1, 52(sp)
    slt t2, t1, t0
    sw t1, 52(sp)
    beq x0, t2, _L3
    la t0, state
    lw t1, 0(t0)
    li t0, 1
    mul t2, t1, t0
    li t0, 1531011
    add t1, t2, t0
    li t0, 32768
    rem t2, t1, t0
    mv t0, t2
    la t0, a
    li t1, 0
    li t3, 4
    lw t4, 52(sp)
    mul t5, t4, t3
    add t3, t1, t5
    mv t1, t3
    add t3, t1, t0
    mv t5, t3
    lw t3, 0(t5)
    add t3, t1, t0
    mv t0, t3
    sw t2, 0(t0)
    sw t4, 52(sp)
_L2:
    li t0, 1
    lw t1, 52(sp)
    add t2, t1, t0
    mv t1, t2
    sw t1, 52(sp)
    j _L1
_L3:
    la t0, a
    li t1, 1
    li t2, 0
    li t3, 4
    mul t4, t1, t3
    add t1, t2, t4
    mv t2, t1
    add t1, t2, t0
    mv t0, t1
    lw t1, 0(t0)
    mv a0, t1
    j main_exit
    # end of body
    
main_exit:
    # start of epilogue
    addi sp, sp, 0
    lw ra, 44(sp)
    lw fp, 48(sp)
    addi sp, sp, 56
    # end of epilogue
    
    ret