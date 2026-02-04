	.file	"cpu4_thread10_fifo.c"
	.text
	.local	A
	.comm	A,32768,32
	.local	B
	.comm	B,32768,32
	.local	C
	.comm	C,32768,32
	.local	tc0
	.comm	tc0,8,8
	.local	tc1
	.comm	tc1,8,8
	.local	tc2
	.comm	tc2,8,8
	.local	tc3
	.comm	tc3,8,8
	.local	tc4
	.comm	tc4,8,8
	.local	tf0
	.comm	tf0,8,8
	.local	tf1
	.comm	tf1,8,8
	.local	tf2
	.comm	tf2,8,8
	.local	tf3
	.comm	tf3,8,8
	.local	tf4
	.comm	tf4,8,8
	.local	tf5
	.comm	tf5,8,8
	.local	tf6
	.comm	tf6,8,8
	.local	tf7
	.comm	tf7,8,8
	.local	tf8
	.comm	tf8,8,8
	.local	tf9
	.comm	tf9,8,8
	.local	tf10
	.comm	tf10,8,8
	.local	tf11
	.comm	tf11,8,8
	.type	init_matrices, @function
init_matrices:
.LFB6:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	movl	$0, -8(%rbp)
	jmp	.L2
.L5:
	movl	$0, -4(%rbp)
	jmp	.L3
.L4:
	movl	-8(%rbp), %edx
	movl	-4(%rbp), %eax
	addl	%edx, %eax
	addl	$1, %eax
	cvtsi2sdl	%eax, %xmm0
	movl	-4(%rbp), %eax
	cltq
	movl	-8(%rbp), %edx
	movslq	%edx, %rdx
	salq	$6, %rdx
	addq	%rdx, %rax
	leaq	0(,%rax,8), %rdx
	leaq	A(%rip), %rax
	movsd	%xmm0, (%rdx,%rax)
	movl	-8(%rbp), %eax
	leal	(%rax,%rax), %edx
	movl	-4(%rbp), %eax
	addl	%edx, %eax
	addl	$3, %eax
	cvtsi2sdl	%eax, %xmm0
	movl	-4(%rbp), %eax
	cltq
	movl	-8(%rbp), %edx
	movslq	%edx, %rdx
	salq	$6, %rdx
	addq	%rdx, %rax
	leaq	0(,%rax,8), %rdx
	leaq	B(%rip), %rax
	movsd	%xmm0, (%rdx,%rax)
	movl	-4(%rbp), %eax
	cltq
	movl	-8(%rbp), %edx
	movslq	%edx, %rdx
	salq	$6, %rdx
	addq	%rdx, %rax
	leaq	0(,%rax,8), %rdx
	leaq	C(%rip), %rax
	pxor	%xmm0, %xmm0
	movsd	%xmm0, (%rdx,%rax)
	addl	$1, -4(%rbp)
.L3:
	cmpl	$63, -4(%rbp)
	jle	.L4
	addl	$1, -8(%rbp)
.L2:
	cmpl	$63, -8(%rbp)
	jle	.L5
	nop
	nop
	popq	%rbp
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE6:
	.size	init_matrices, .-init_matrices
	.type	busy_wait_seconds, @function
busy_wait_seconds:
.LFB7:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	movsd	%xmm0, -40(%rbp)
	movsd	-40(%rbp), %xmm1
	movsd	.LC1(%rip), %xmm0
	mulsd	%xmm0, %xmm1
	movsd	.LC2(%rip), %xmm0
	mulsd	%xmm1, %xmm0
	cvttsd2sil	%xmm0, %eax
	movl	%eax, -28(%rbp)
	cmpl	$0, -28(%rbp)
	jg	.L7
	movl	$1, -28(%rbp)
.L7:
	movl	$0, -24(%rbp)
	jmp	.L8
.L15:
	movl	$0, -20(%rbp)
	jmp	.L9
.L14:
	movl	$0, -16(%rbp)
	jmp	.L10
.L13:
	pxor	%xmm0, %xmm0
	movsd	%xmm0, -8(%rbp)
	movl	$0, -12(%rbp)
	jmp	.L11
.L12:
	movl	-12(%rbp), %eax
	cltq
	movl	-20(%rbp), %edx
	movslq	%edx, %rdx
	salq	$6, %rdx
	addq	%rdx, %rax
	leaq	0(,%rax,8), %rdx
	leaq	A(%rip), %rax
	movsd	(%rdx,%rax), %xmm1
	movl	-16(%rbp), %eax
	cltq
	movl	-12(%rbp), %edx
	movslq	%edx, %rdx
	salq	$6, %rdx
	addq	%rdx, %rax
	leaq	0(,%rax,8), %rdx
	leaq	B(%rip), %rax
	movsd	(%rdx,%rax), %xmm0
	mulsd	%xmm1, %xmm0
	movsd	-8(%rbp), %xmm1
	addsd	%xmm1, %xmm0
	movsd	%xmm0, -8(%rbp)
	addl	$1, -12(%rbp)
.L11:
	cmpl	$63, -12(%rbp)
	jle	.L12
	movl	-16(%rbp), %eax
	cltq
	movl	-20(%rbp), %edx
	movslq	%edx, %rdx
	salq	$6, %rdx
	addq	%rdx, %rax
	leaq	0(,%rax,8), %rdx
	leaq	C(%rip), %rax
	movsd	-8(%rbp), %xmm0
	movsd	%xmm0, (%rdx,%rax)
	addl	$1, -16(%rbp)
.L10:
	cmpl	$63, -16(%rbp)
	jle	.L13
	addl	$1, -20(%rbp)
.L9:
	cmpl	$63, -20(%rbp)
	jle	.L14
	addl	$1, -24(%rbp)
.L8:
	movl	-24(%rbp), %eax
	cmpl	-28(%rbp), %eax
	jl	.L15
	nop
	nop
	popq	%rbp
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE7:
	.size	busy_wait_seconds, .-busy_wait_seconds
	.local	g_prog_start
	.comm	g_prog_start,16,16
	.section	.rodata
.LC4:
	.string	"c4"
.LC5:
	.string	"%s start (CPU %d) at %.3fs\n"
	.align 8
.LC8:
	.string	"%s done (CPU %d, target %.3fs, real %.3fs)\n"
	.text
	.type	c4_fn, @function
c4_fn:
.LFB8:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC4(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC6(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC7(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC4(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L18
	call	__stack_chk_fail@PLT
.L18:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE8:
	.size	c4_fn, .-c4_fn
	.section	.rodata
.LC9:
	.string	"c3"
	.text
	.type	c3_fn, @function
c3_fn:
.LFB9:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC9(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC10(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC11(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC9(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %ecx
	leaq	c4_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tc4(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L21
	call	__stack_chk_fail@PLT
.L21:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE9:
	.size	c3_fn, .-c3_fn
	.section	.rodata
.LC12:
	.string	"c2"
	.text
	.type	c2_fn, @function
c2_fn:
.LFB10:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC12(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC13(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC14(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC12(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %ecx
	leaq	c3_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tc3(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L24
	call	__stack_chk_fail@PLT
.L24:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE10:
	.size	c2_fn, .-c2_fn
	.section	.rodata
.LC15:
	.string	"c1"
	.text
	.type	c1_fn, @function
c1_fn:
.LFB11:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC15(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC16(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC17(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC15(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %ecx
	leaq	c2_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tc2(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L27
	call	__stack_chk_fail@PLT
.L27:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE11:
	.size	c1_fn, .-c1_fn
	.section	.rodata
.LC18:
	.string	"c0"
	.text
	.type	c0_fn, @function
c0_fn:
.LFB12:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC18(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC19(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC20(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC18(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %ecx
	leaq	c1_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tc1(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L30
	call	__stack_chk_fail@PLT
.L30:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE12:
	.size	c0_fn, .-c0_fn
	.section	.rodata
.LC21:
	.string	"f0"
	.text
	.type	f0_fn, @function
f0_fn:
.LFB13:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC21(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC21(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L33
	call	__stack_chk_fail@PLT
.L33:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE13:
	.size	f0_fn, .-f0_fn
	.section	.rodata
.LC24:
	.string	"f1"
	.text
	.type	f1_fn, @function
f1_fn:
.LFB14:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC24(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC24(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L36
	call	__stack_chk_fail@PLT
.L36:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE14:
	.size	f1_fn, .-f1_fn
	.section	.rodata
.LC25:
	.string	"f2"
	.text
	.type	f2_fn, @function
f2_fn:
.LFB15:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC25(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC25(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L39
	call	__stack_chk_fail@PLT
.L39:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE15:
	.size	f2_fn, .-f2_fn
	.section	.rodata
.LC26:
	.string	"f3"
	.text
	.type	f3_fn, @function
f3_fn:
.LFB16:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC26(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC26(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L42
	call	__stack_chk_fail@PLT
.L42:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE16:
	.size	f3_fn, .-f3_fn
	.section	.rodata
.LC27:
	.string	"f4"
	.text
	.type	f4_fn, @function
f4_fn:
.LFB17:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC27(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC27(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L45
	call	__stack_chk_fail@PLT
.L45:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE17:
	.size	f4_fn, .-f4_fn
	.section	.rodata
.LC28:
	.string	"f5"
	.text
	.type	f5_fn, @function
f5_fn:
.LFB18:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC28(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC28(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L48
	call	__stack_chk_fail@PLT
.L48:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE18:
	.size	f5_fn, .-f5_fn
	.section	.rodata
.LC29:
	.string	"f6"
	.text
	.type	f6_fn, @function
f6_fn:
.LFB19:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC29(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC29(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L51
	call	__stack_chk_fail@PLT
.L51:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE19:
	.size	f6_fn, .-f6_fn
	.section	.rodata
.LC30:
	.string	"f7"
	.text
	.type	f7_fn, @function
f7_fn:
.LFB20:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC30(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC30(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L54
	call	__stack_chk_fail@PLT
.L54:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE20:
	.size	f7_fn, .-f7_fn
	.section	.rodata
.LC31:
	.string	"f8"
	.text
	.type	f8_fn, @function
f8_fn:
.LFB21:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC31(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC31(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L57
	call	__stack_chk_fail@PLT
.L57:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE21:
	.size	f8_fn, .-f8_fn
	.section	.rodata
.LC32:
	.string	"f9"
	.text
	.type	f9_fn, @function
f9_fn:
.LFB22:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC32(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC32(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L60
	call	__stack_chk_fail@PLT
.L60:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE22:
	.size	f9_fn, .-f9_fn
	.section	.rodata
.LC33:
	.string	"f10"
	.text
	.type	f10_fn, @function
f10_fn:
.LFB23:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC33(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC22(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC23(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC33(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L63
	call	__stack_chk_fail@PLT
.L63:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE23:
	.size	f10_fn, .-f10_fn
	.section	.rodata
.LC34:
	.string	"f11"
	.text
	.type	f11_fn, @function
f11_fn:
.LFB24:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$80, %rsp
	movq	%rdi, -72(%rbp)
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-48(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-48(%rbp), %rdx
	movq	g_prog_start(%rip), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-40(%rbp), %rcx
	movq	8+g_prog_start(%rip), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -64(%rbp)
	cvtsi2sdq	-64(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movsd	-80(%rbp), %xmm0
	movl	%eax, %edx
	leaq	.LC34(%rip), %rsi
	leaq	.LC5(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	movq	.LC35(%rip), %rax
	movq	%rax, %xmm0
	call	busy_wait_seconds
	leaq	-32(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-32(%rbp), %rdx
	movq	-48(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-24(%rbp), %rcx
	movq	-40(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -56(%rbp)
	cvtsi2sdq	-56(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	movsd	%xmm0, -80(%rbp)
	call	sched_getcpu@PLT
	movl	%eax, %edx
	movq	.LC36(%rip), %rax
	movsd	-80(%rbp), %xmm1
	movq	%rax, %xmm0
	leaq	.LC34(%rip), %rsi
	leaq	.LC8(%rip), %rdi
	movl	$2, %eax
	call	printf@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rsi
	xorq	%fs:40, %rsi
	je	.L66
	call	__stack_chk_fail@PLT
.L66:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE24:
	.size	f11_fn, .-f11_fn
	.section	.rodata
.LC37:
	.string	"sched_setaffinity failed: %s\n"
.LC38:
	.string	"Program total time: %.3fs\n"
.LC39:
	.string	"all threads done"
	.text
	.globl	main
	.type	main, @function
main:
.LFB25:
	.cfi_startproc
	endbr64
	pushq	%rbp
	.cfi_def_cfa_offset 16
	.cfi_offset 6, -16
	movq	%rsp, %rbp
	.cfi_def_cfa_register 6
	subq	$224, %rsp
	movq	%fs:40, %rax
	movq	%rax, -8(%rbp)
	xorl	%eax, %eax
	leaq	-144(%rbp), %rax
	movq	%rax, %rsi
	movl	$0, %eax
	movl	$16, %edx
	movq	%rsi, %rdi
	movq	%rdx, %rcx
	rep stosq
	movq	$0, -216(%rbp)
	cmpq	$1023, -216(%rbp)
	ja	.L69
	movq	-216(%rbp), %rax
	shrq	$6, %rax
	leaq	0(,%rax,8), %rdx
	leaq	-144(%rbp), %rcx
	addq	%rcx, %rdx
	movq	(%rdx), %rdx
	movq	-216(%rbp), %rcx
	andl	$63, %ecx
	movl	$1, %esi
	salq	%cl, %rsi
	movq	%rsi, %rcx
	leaq	0(,%rax,8), %rsi
	leaq	-144(%rbp), %rax
	addq	%rsi, %rax
	orq	%rcx, %rdx
	movq	%rdx, (%rax)
.L69:
	movq	$1, -208(%rbp)
	cmpq	$1023, -208(%rbp)
	ja	.L71
	movq	-208(%rbp), %rax
	shrq	$6, %rax
	leaq	0(,%rax,8), %rdx
	leaq	-144(%rbp), %rcx
	addq	%rcx, %rdx
	movq	(%rdx), %rdx
	movq	-208(%rbp), %rcx
	andl	$63, %ecx
	movl	$1, %esi
	salq	%cl, %rsi
	movq	%rsi, %rcx
	leaq	0(,%rax,8), %rsi
	leaq	-144(%rbp), %rax
	addq	%rsi, %rax
	orq	%rcx, %rdx
	movq	%rdx, (%rax)
.L71:
	movq	$2, -200(%rbp)
	cmpq	$1023, -200(%rbp)
	ja	.L73
	movq	-200(%rbp), %rax
	shrq	$6, %rax
	leaq	0(,%rax,8), %rdx
	leaq	-144(%rbp), %rcx
	addq	%rcx, %rdx
	movq	(%rdx), %rdx
	movq	-200(%rbp), %rcx
	andl	$63, %ecx
	movl	$1, %esi
	salq	%cl, %rsi
	movq	%rsi, %rcx
	leaq	0(,%rax,8), %rsi
	leaq	-144(%rbp), %rax
	addq	%rsi, %rax
	orq	%rcx, %rdx
	movq	%rdx, (%rax)
.L73:
	movq	$3, -192(%rbp)
	cmpq	$1023, -192(%rbp)
	ja	.L75
	movq	-192(%rbp), %rax
	shrq	$6, %rax
	leaq	0(,%rax,8), %rdx
	leaq	-144(%rbp), %rcx
	addq	%rcx, %rdx
	movq	(%rdx), %rdx
	movq	-192(%rbp), %rcx
	andl	$63, %ecx
	movl	$1, %esi
	salq	%cl, %rsi
	movq	%rsi, %rcx
	leaq	0(,%rax,8), %rsi
	leaq	-144(%rbp), %rax
	addq	%rsi, %rax
	orq	%rcx, %rdx
	movq	%rdx, (%rax)
.L75:
	leaq	-144(%rbp), %rax
	movq	%rax, %rdx
	movl	$128, %esi
	movl	$0, %edi
	call	sched_setaffinity@PLT
	testl	%eax, %eax
	je	.L76
	call	__errno_location@PLT
	movl	(%rax), %eax
	movl	%eax, %edi
	call	strerror@PLT
	movq	%rax, %rdx
	movq	stderr(%rip), %rax
	leaq	.LC37(%rip), %rsi
	movq	%rax, %rdi
	movl	$0, %eax
	call	fprintf@PLT
.L76:
	call	init_matrices
	leaq	g_prog_start(%rip), %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	leaq	-176(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movl	$0, %ecx
	leaq	f0_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf0(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f1_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf1(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f2_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf2(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f3_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf3(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f4_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf4(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f5_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf5(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f6_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf6(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f7_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf7(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f8_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf8(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f9_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf9(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f10_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf10(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	f11_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tf11(%rip), %rdi
	call	pthread_create@PLT
	movl	$0, %ecx
	leaq	c0_fn(%rip), %rdx
	movl	$0, %esi
	leaq	tc0(%rip), %rdi
	call	pthread_create@PLT
	movq	tc0(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tc1(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tc2(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tc3(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tc4(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf0(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf1(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf2(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf3(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf4(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf5(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf6(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf7(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf8(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf9(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf10(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	movq	tf11(%rip), %rax
	movl	$0, %esi
	movq	%rax, %rdi
	call	pthread_join@PLT
	leaq	-160(%rbp), %rax
	movq	%rax, %rsi
	movl	$1, %edi
	call	clock_gettime@PLT
	movq	-160(%rbp), %rdx
	movq	-176(%rbp), %rax
	subq	%rax, %rdx
	movq	%rdx, %rax
	imulq	$1000000000, %rax, %rax
	movq	-152(%rbp), %rcx
	movq	-168(%rbp), %rdx
	subq	%rdx, %rcx
	movq	%rcx, %rdx
	addq	%rdx, %rax
	movq	%rax, -184(%rbp)
	cvtsi2sdq	-184(%rbp), %xmm0
	movsd	.LC3(%rip), %xmm1
	divsd	%xmm1, %xmm0
	leaq	.LC38(%rip), %rdi
	movl	$1, %eax
	call	printf@PLT
	leaq	.LC39(%rip), %rdi
	call	puts@PLT
	movl	$0, %eax
	movq	-8(%rbp), %rdi
	xorq	%fs:40, %rdi
	je	.L78
	call	__stack_chk_fail@PLT
.L78:
	leave
	.cfi_def_cfa 7, 8
	ret
	.cfi_endproc
.LFE25:
	.size	main, .-main
	.section	.rodata
	.align 8
.LC1:
	.long	0
	.long	1087924736
	.align 8
.LC2:
	.long	2576980378
	.long	1069128089
	.align 8
.LC3:
	.long	0
	.long	1104006501
	.align 8
.LC6:
	.long	0
	.long	1076887552
	.align 8
.LC7:
	.long	2576980378
	.long	1073322393
	.align 8
.LC10:
	.long	0
	.long	1077018624
	.align 8
.LC11:
	.long	3435973837
	.long	1073532108
	.align 8
.LC13:
	.long	0
	.long	1077149696
	.align 8
.LC14:
	.long	0
	.long	1073741824
	.align 8
.LC16:
	.long	0
	.long	1077280768
	.align 8
.LC17:
	.long	2576980378
	.long	1073846681
	.align 8
.LC19:
	.long	0
	.long	1077477376
	.align 8
.LC20:
	.long	0
	.long	1074003968
	.align 8
.LC22:
	.long	0
	.long	1075052544
	.align 8
.LC23:
	.long	0
	.long	1071644672
	.align 8
.LC35:
	.long	0
	.long	1074266112
	.align 8
.LC36:
	.long	858993460
	.long	1070805811
	.ident	"GCC: (Ubuntu 9.4.0-1ubuntu1~20.04.2) 9.4.0"
	.section	.note.GNU-stack,"",@progbits
	.section	.note.gnu.property,"a"
	.align 8
	.long	 1f - 0f
	.long	 4f - 1f
	.long	 5
0:
	.string	 "GNU"
1:
	.align 8
	.long	 0xc0000002
	.long	 3f - 2f
2:
	.long	 0x3
3:
	.align 8
4:
