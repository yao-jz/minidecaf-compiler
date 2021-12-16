   .bss
    .global C
    C:
        .space 80000
    .data
    .global P
    P:
        .word 10000007
    .text
    .global main
    
main:
    # start of prologue
    addi sp, sp, -72
    sw ra, 44(sp)
    sw fp, 48(sp)
    # end of prologue
    
    # start of body
    li t0, 5996
    mv t1, t0
    li t0, 1
    la t2, C
    li t3, 0
    li t4, 0
    li t5, 0
    li t6, 40000
    li a0, 4
    mul a1, t3, t6
    add t3, t5, a1
    mv t5, t3
    mul t3, t4, a0
    add t4, t5, t3
    mv t5, t4
    add t3, t5, t2
    mv t4, t3
    lw t3, 0(t4)
    add t3, t5, t2
    mv t2, t3
    sw t0, 0(t2)
    li t0, 0
    mv t2, t0
    li t0, 1
    mv t3, t0
    sw t1, 52(sp)
    sw t2, 56(sp)
    sw t3, 60(sp)
_L1:
    lw t0, 60(sp)
    lw t1, 52(sp)
    sw t0, -4(sp)
        sgt t0, t0, t1
        xori t2, t0, 1
        lw t0, -4(sp)
    sw t1, 52(sp)
    sw t0, 60(sp)
    beq x0, t2, _L3
    li t0, 0
    mv t1, t0
    sw t1, 64(sp)
_L4:
    lw t0, 64(sp)
    lw t1, 60(sp)
    sw t0, -4(sp)
        sgt t0, t0, t1
        xori t2, t0, 1
        lw t0, -4(sp)
    sw t1, 60(sp)
    sw t0, 64(sp)
    beq x0, t2, _L6
    lw t0, 64(sp)
    seqz t1, t0
    sw t0, 64(sp)
    beq x0, t1, _L7
    li t0, 1
    mv t1, t0
    sw t1, 68(sp)
    j _L8
_L7:
    la t0, C
    li t1, 0
    li t2, 40000
    li t3, 4
    lw t4, 56(sp)
    mul t5, t4, t2
    add t2, t1, t5
    mv t1, t2
    lw t2, 64(sp)
    mul t5, t2, t3
    add t3, t1, t5
    mv t1, t3
    add t3, t1, t0
    mv t0, t3
    lw t1, 0(t0)
    la t0, C
    li t3, 1
    sub t5, t2, t3
    li t3, 0
    li t6, 40000
    li a0, 4
    mul a1, t4, t6
    add t6, t3, a1
    mv t3, t6
    mul t6, t5, a0
    add t5, t3, t6
    mv t3, t5
    add t5, t3, t0
    mv t0, t5
    lw t3, 0(t0)
    add t0, t1, t3
    la t1, P
    lw t3, 0(t1)
    rem t1, t0, t3
    mv t0, t1
    sw t4, 56(sp)
    sw t2, 64(sp)
    sw t0, 68(sp)
_L8:
    la t0, C
    li t1, 1
    lw t2, 56(sp)
    sub t3, t1, t2
    li t1, 0
    li t4, 40000
    li t5, 4
    mul t6, t3, t4
    add t3, t1, t6
    mv t1, t3
    lw t3, 64(sp)
    mul t4, t3, t5
    add t5, t1, t4
    mv t1, t5
    add t4, t1, t0
    mv t5, t4
    lw t4, 0(t5)
    add t4, t1, t0
    mv t0, t4
    lw t1, 68(sp)
    sw t1, 0(t0)
    sw t2, 56(sp)
    sw t3, 64(sp)
_L5:
    li t0, 1
    lw t1, 64(sp)
    add t2, t1, t0
    mv t1, t2
    sw t1, 64(sp)
    j _L4
_L6:
    li t0, 1
    lw t1, 56(sp)
    sub t2, t0, t1
    mv t1, t2
    sw t1, 56(sp)
_L2:
    li t0, 1
    lw t1, 60(sp)
    add t2, t1, t0
    mv t1, t2
    sw t1, 60(sp)
    j _L1
_L3:
    li t0, 0
    mv a0, t0
    j main_exit
    # end of body
    
main_exit:
    # start of epilogue
    addi sp, sp, 0
    lw ra, 44(sp)
    lw fp, 48(sp)
    addi sp, sp, 72
    # end of epilogue
    
    ret