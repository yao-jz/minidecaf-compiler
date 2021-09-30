	.file	"main.c"
	.option nopic
	.attribute arch, "rv32i2p0_m2p0"
	.attribute unaligned_access, 0
	.attribute stack_align, 16
	.text
	.section	.text.startup,"ax",@progbits
	.align	2
	.globl	main
	.type	main, @function
main:
	sub	a0,a0,a1
	snez	a0,a0
	ret
	.size	main, .-main
	.ident	"GCC: (SiFive GCC 8.3.0-2020.04.0) 8.3.0"
