#define _GNU_SOURCE
#include "time_stat.h"  // TA_INCLUDE
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

/* 固定矩阵规模和重复次数，循环内不调用函数 */
#define MAT_N 64
#define REPEAT0 16
#define REPEAT1 18
#define REPEAT2 20
#define REPEAT3 22
#define REPEAT4 24
#define REPEAT5 26
#define REPEAT6 28
#define REPEAT7 30
#define REPEAT8 34
#define REPEAT9 38

/* 全局矩阵，避免在线程函数里分配 */
static double A[MAT_N][MAT_N];
static double B[MAT_N][MAT_N];
static double C[MAT_N][MAT_N];

/* 每个线程独立函数，循环内无函数调用，负载刻意拉开差异 */
static void *worker0(void *arg)
{
    int base = 0 * 5 + 1;
    for (int r = 0; r < REPEAT0; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:43 printf
; /* TA_PAD */
uint64_t __ta_t0_worker0_printf1_43_95 = now_ns();
    printf("worker0 done\n");
// TA_END: cpu4_thread10.c:43 printf
uint64_t __ta_t0_worker0_printf1_43_95_dur = now_ns() - __ta_t0_worker0_printf1_43_95;
time_account("worker0/printf1", __ta_t0_worker0_printf1_43_95_dur);
time_trace("worker0/printf1", __ta_t0_worker0_printf1_43_95, __ta_t0_worker0_printf1_43_95_dur);
    return NULL;
}

static void *worker1(void *arg)
{
    int base = 1 * 5 + 1;
    for (int r = 0; r < REPEAT1; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:61 printf
; /* TA_PAD */
uint64_t __ta_t0_worker1_printf1_61_94 = now_ns();
    printf("worker1 done\n");
// TA_END: cpu4_thread10.c:61 printf
uint64_t __ta_t0_worker1_printf1_61_94_dur = now_ns() - __ta_t0_worker1_printf1_61_94;
time_account("worker1/printf1", __ta_t0_worker1_printf1_61_94_dur);
time_trace("worker1/printf1", __ta_t0_worker1_printf1_61_94, __ta_t0_worker1_printf1_61_94_dur);
    return NULL;
}

static void *worker2(void *arg)
{
    int base = 2 * 5 + 1;
    for (int r = 0; r < REPEAT2; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:79 printf
; /* TA_PAD */
uint64_t __ta_t0_worker2_printf1_79_93 = now_ns();
    printf("worker2 done\n");
// TA_END: cpu4_thread10.c:79 printf
uint64_t __ta_t0_worker2_printf1_79_93_dur = now_ns() - __ta_t0_worker2_printf1_79_93;
time_account("worker2/printf1", __ta_t0_worker2_printf1_79_93_dur);
time_trace("worker2/printf1", __ta_t0_worker2_printf1_79_93, __ta_t0_worker2_printf1_79_93_dur);
}

static void *worker3(void *arg)
{
    int base = 3 * 5 + 1;
    for (int r = 0; r < REPEAT3; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:96 printf
; /* TA_PAD */
uint64_t __ta_t0_worker3_printf1_96_92 = now_ns();
    printf("worker3 done\n");
// TA_END: cpu4_thread10.c:96 printf
uint64_t __ta_t0_worker3_printf1_96_92_dur = now_ns() - __ta_t0_worker3_printf1_96_92;
time_account("worker3/printf1", __ta_t0_worker3_printf1_96_92_dur);
time_trace("worker3/printf1", __ta_t0_worker3_printf1_96_92, __ta_t0_worker3_printf1_96_92_dur);
    return NULL;
}

static void *worker4(void *arg)
{
    int base = 4 * 5 + 1;
    for (int r = 0; r < REPEAT4; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:114 printf
; /* TA_PAD */
uint64_t __ta_t0_worker4_printf1_114_91 = now_ns();
    printf("worker4 done\n");
// TA_END: cpu4_thread10.c:114 printf
uint64_t __ta_t0_worker4_printf1_114_91_dur = now_ns() - __ta_t0_worker4_printf1_114_91;
time_account("worker4/printf1", __ta_t0_worker4_printf1_114_91_dur);
time_trace("worker4/printf1", __ta_t0_worker4_printf1_114_91, __ta_t0_worker4_printf1_114_91_dur);
    return NULL;
}

static void *worker5(void *arg)
{
    int base = 5 * 5 + 1;
    for (int r = 0; r < REPEAT5; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:132 printf
; /* TA_PAD */
uint64_t __ta_t0_worker5_printf1_132_90 = now_ns();
    printf("worker5 done\n");
// TA_END: cpu4_thread10.c:132 printf
uint64_t __ta_t0_worker5_printf1_132_90_dur = now_ns() - __ta_t0_worker5_printf1_132_90;
time_account("worker5/printf1", __ta_t0_worker5_printf1_132_90_dur);
time_trace("worker5/printf1", __ta_t0_worker5_printf1_132_90, __ta_t0_worker5_printf1_132_90_dur);
    return NULL;
}

static void *worker6(void *arg)
{
    int base = 6 * 5 + 1;
    for (int r = 0; r < REPEAT6; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:150 printf
; /* TA_PAD */
uint64_t __ta_t0_worker6_printf1_150_89 = now_ns();
    printf("worker6 done\n");
// TA_END: cpu4_thread10.c:150 printf
uint64_t __ta_t0_worker6_printf1_150_89_dur = now_ns() - __ta_t0_worker6_printf1_150_89;
time_account("worker6/printf1", __ta_t0_worker6_printf1_150_89_dur);
time_trace("worker6/printf1", __ta_t0_worker6_printf1_150_89, __ta_t0_worker6_printf1_150_89_dur);
    return NULL;
}

static void *worker7(void *arg)
{
    int base = 7 * 5 + 1;
    for (int r = 0; r < REPEAT7; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:168 printf
; /* TA_PAD */
uint64_t __ta_t0_worker7_printf1_168_88 = now_ns();
    printf("worker7 done\n");
// TA_END: cpu4_thread10.c:168 printf
uint64_t __ta_t0_worker7_printf1_168_88_dur = now_ns() - __ta_t0_worker7_printf1_168_88;
time_account("worker7/printf1", __ta_t0_worker7_printf1_168_88_dur);
time_trace("worker7/printf1", __ta_t0_worker7_printf1_168_88, __ta_t0_worker7_printf1_168_88_dur);
    return NULL;
}

static void *worker8(void *arg)
{
    int base = 8 * 5 + 1;
    for (int r = 0; r < REPEAT8; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:186 printf
; /* TA_PAD */
uint64_t __ta_t0_worker8_printf1_186_87 = now_ns();
    printf("worker8 done\n");
// TA_END: cpu4_thread10.c:186 printf
uint64_t __ta_t0_worker8_printf1_186_87_dur = now_ns() - __ta_t0_worker8_printf1_186_87;
time_account("worker8/printf1", __ta_t0_worker8_printf1_186_87_dur);
time_trace("worker8/printf1", __ta_t0_worker8_printf1_186_87, __ta_t0_worker8_printf1_186_87_dur);
    return NULL;
}

static void *worker9(void *arg)
{
    int base = 9 * 5 + 1;
    for (int r = 0; r < REPEAT9; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
// TA_BEGIN: cpu4_thread10.c:204 printf
; /* TA_PAD */
uint64_t __ta_t0_worker9_printf1_204_86 = now_ns();
    printf("worker9 done\n");
// TA_END: cpu4_thread10.c:204 printf
uint64_t __ta_t0_worker9_printf1_204_86_dur = now_ns() - __ta_t0_worker9_printf1_204_86;
time_account("worker9/printf1", __ta_t0_worker9_printf1_204_86_dur);
time_trace("worker9/printf1", __ta_t0_worker9_printf1_204_86, __ta_t0_worker9_printf1_204_86_dur);
    return NULL;
}

int main(void)
{
    /* 预填充矩阵：循环里只有算术，没有函数调用 */
    for (int i = 0; i < MAT_N; i++) {
        for (int j = 0; j < MAT_N; j++) {
            A[i][j] = (double)(i + j + 1);
            B[i][j] = (double)(i * 2 + j + 3);
            C[i][j] = 0.0;
        }
    }

    /* 约束进程跑在前 4 个核心（可选） */
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    CPU_SET(1, &set);
    CPU_SET(2, &set);
    CPU_SET(3, &set);
    if ((__extension__({ uint64_t __ta_t0_main_sched_setaffinity1_226_85 = now_ns(); __auto_type __ta_ret = sched_setaffinity(0, sizeof(set), &set); uint64_t __ta_t0_main_sched_setaffinity1_226_85_dur = now_ns() - __ta_t0_main_sched_setaffinity1_226_85; time_account("main/sched_setaffinity1", __ta_t0_main_sched_setaffinity1_226_85_dur); time_trace("main/sched_setaffinity1", __ta_t0_main_sched_setaffinity1_226_85, __ta_t0_main_sched_setaffinity1_226_85_dur); __ta_ret; })) != 0) {
// TA_BEGIN: cpu4_thread10.c:227 fprintf
; /* TA_PAD */
uint64_t __ta_t0_main_fprintf4_227_84 = now_ns();
// TA_BEGIN: cpu4_thread10.c:227 strerror
; /* TA_PAD */
// TA_END: cpu4_thread10.c:227 fprintf
uint64_t __ta_t0_main_fprintf4_227_84_dur = now_ns() - __ta_t0_main_fprintf4_227_84;
time_account("main/fprintf4", __ta_t0_main_fprintf4_227_84_dur);
time_trace("main/fprintf4", __ta_t0_main_fprintf4_227_84, __ta_t0_main_fprintf4_227_84_dur);
uint64_t __ta_t0_main_strerror3_227_83 = now_ns();
// TA_BEGIN: cpu4_thread10.c:227 __errno_location
; /* TA_PAD */
// TA_END: cpu4_thread10.c:227 strerror
uint64_t __ta_t0_main_strerror3_227_83_dur = now_ns() - __ta_t0_main_strerror3_227_83;
time_account("main/strerror3", __ta_t0_main_strerror3_227_83_dur);
time_trace("main/strerror3", __ta_t0_main_strerror3_227_83, __ta_t0_main_strerror3_227_83_dur);
uint64_t __ta_t0_main___errno_location2_227_82 = now_ns();
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
// TA_END: cpu4_thread10.c:227 __errno_location
uint64_t __ta_t0_main___errno_location2_227_82_dur = now_ns() - __ta_t0_main___errno_location2_227_82;
time_account("main/__errno_location2", __ta_t0_main___errno_location2_227_82_dur);
time_trace("main/__errno_location2", __ta_t0_main___errno_location2_227_82, __ta_t0_main___errno_location2_227_82_dur);
    }

    pthread_t t0, t1, t2, t3, t4, t5, t6, t7, t8, t9;
    int prio = 60;

    /* t0 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:237 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init5_237_81 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:237 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init5_237_81_dur = now_ns() - __ta_t0_main_pthread_attr_init5_237_81;
time_account("main/pthread_attr_init5", __ta_t0_main_pthread_attr_init5_237_81_dur);
time_trace("main/pthread_attr_init5", __ta_t0_main_pthread_attr_init5_237_81, __ta_t0_main_pthread_attr_init5_237_81_dur);
// TA_BEGIN: cpu4_thread10.c:238 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched6_238_80 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:238 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched6_238_80_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched6_238_80;
time_account("main/pthread_attr_setinheritsched6", __ta_t0_main_pthread_attr_setinheritsched6_238_80_dur);
time_trace("main/pthread_attr_setinheritsched6", __ta_t0_main_pthread_attr_setinheritsched6_238_80, __ta_t0_main_pthread_attr_setinheritsched6_238_80_dur);
// TA_BEGIN: cpu4_thread10.c:239 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy7_239_79 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:239 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy7_239_79_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy7_239_79;
time_account("main/pthread_attr_setschedpolicy7", __ta_t0_main_pthread_attr_setschedpolicy7_239_79_dur);
time_trace("main/pthread_attr_setschedpolicy7", __ta_t0_main_pthread_attr_setschedpolicy7_239_79, __ta_t0_main_pthread_attr_setschedpolicy7_239_79_dur);
// TA_BEGIN: cpu4_thread10.c:240 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset8_240_78 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:240 memset
uint64_t __ta_t0_main_memset8_240_78_dur = now_ns() - __ta_t0_main_memset8_240_78;
time_account("main/memset8", __ta_t0_main_memset8_240_78_dur);
time_trace("main/memset8", __ta_t0_main_memset8_240_78, __ta_t0_main_memset8_240_78_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:242 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam9_242_77 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:242 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam9_242_77_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam9_242_77;
time_account("main/pthread_attr_setschedparam9", __ta_t0_main_pthread_attr_setschedparam9_242_77_dur);
time_trace("main/pthread_attr_setschedparam9", __ta_t0_main_pthread_attr_setschedparam9_242_77, __ta_t0_main_pthread_attr_setschedparam9_242_77_dur);
// TA_BEGIN: cpu4_thread10.c:243 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create10_243_76 = now_ns();
        pthread_create(&t0, &attr, worker0, NULL);
// TA_END: cpu4_thread10.c:243 pthread_create
uint64_t __ta_t0_main_pthread_create10_243_76_dur = now_ns() - __ta_t0_main_pthread_create10_243_76;
time_account("main/pthread_create10", __ta_t0_main_pthread_create10_243_76_dur);
time_trace("main/pthread_create10", __ta_t0_main_pthread_create10_243_76, __ta_t0_main_pthread_create10_243_76_dur);
// TA_BEGIN: cpu4_thread10.c:244 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy11_244_75 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:244 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy11_244_75_dur = now_ns() - __ta_t0_main_pthread_attr_destroy11_244_75;
time_account("main/pthread_attr_destroy11", __ta_t0_main_pthread_attr_destroy11_244_75_dur);
time_trace("main/pthread_attr_destroy11", __ta_t0_main_pthread_attr_destroy11_244_75, __ta_t0_main_pthread_attr_destroy11_244_75_dur);
    }

    /* t1 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:251 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init12_251_74 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:251 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init12_251_74_dur = now_ns() - __ta_t0_main_pthread_attr_init12_251_74;
time_account("main/pthread_attr_init12", __ta_t0_main_pthread_attr_init12_251_74_dur);
time_trace("main/pthread_attr_init12", __ta_t0_main_pthread_attr_init12_251_74, __ta_t0_main_pthread_attr_init12_251_74_dur);
// TA_BEGIN: cpu4_thread10.c:252 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched13_252_73 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:252 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched13_252_73_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched13_252_73;
time_account("main/pthread_attr_setinheritsched13", __ta_t0_main_pthread_attr_setinheritsched13_252_73_dur);
time_trace("main/pthread_attr_setinheritsched13", __ta_t0_main_pthread_attr_setinheritsched13_252_73, __ta_t0_main_pthread_attr_setinheritsched13_252_73_dur);
// TA_BEGIN: cpu4_thread10.c:253 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy14_253_72 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:253 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy14_253_72_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy14_253_72;
time_account("main/pthread_attr_setschedpolicy14", __ta_t0_main_pthread_attr_setschedpolicy14_253_72_dur);
time_trace("main/pthread_attr_setschedpolicy14", __ta_t0_main_pthread_attr_setschedpolicy14_253_72, __ta_t0_main_pthread_attr_setschedpolicy14_253_72_dur);
// TA_BEGIN: cpu4_thread10.c:254 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset15_254_71 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:254 memset
uint64_t __ta_t0_main_memset15_254_71_dur = now_ns() - __ta_t0_main_memset15_254_71;
time_account("main/memset15", __ta_t0_main_memset15_254_71_dur);
time_trace("main/memset15", __ta_t0_main_memset15_254_71, __ta_t0_main_memset15_254_71_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:256 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam16_256_70 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:256 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam16_256_70_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam16_256_70;
time_account("main/pthread_attr_setschedparam16", __ta_t0_main_pthread_attr_setschedparam16_256_70_dur);
time_trace("main/pthread_attr_setschedparam16", __ta_t0_main_pthread_attr_setschedparam16_256_70, __ta_t0_main_pthread_attr_setschedparam16_256_70_dur);
// TA_BEGIN: cpu4_thread10.c:257 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create17_257_69 = now_ns();
        pthread_create(&t1, &attr, worker1, NULL);
// TA_END: cpu4_thread10.c:257 pthread_create
uint64_t __ta_t0_main_pthread_create17_257_69_dur = now_ns() - __ta_t0_main_pthread_create17_257_69;
time_account("main/pthread_create17", __ta_t0_main_pthread_create17_257_69_dur);
time_trace("main/pthread_create17", __ta_t0_main_pthread_create17_257_69, __ta_t0_main_pthread_create17_257_69_dur);
// TA_BEGIN: cpu4_thread10.c:258 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy18_258_68 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:258 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy18_258_68_dur = now_ns() - __ta_t0_main_pthread_attr_destroy18_258_68;
time_account("main/pthread_attr_destroy18", __ta_t0_main_pthread_attr_destroy18_258_68_dur);
time_trace("main/pthread_attr_destroy18", __ta_t0_main_pthread_attr_destroy18_258_68, __ta_t0_main_pthread_attr_destroy18_258_68_dur);
    }

    /* t2 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:265 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init19_265_67 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:265 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init19_265_67_dur = now_ns() - __ta_t0_main_pthread_attr_init19_265_67;
time_account("main/pthread_attr_init19", __ta_t0_main_pthread_attr_init19_265_67_dur);
time_trace("main/pthread_attr_init19", __ta_t0_main_pthread_attr_init19_265_67, __ta_t0_main_pthread_attr_init19_265_67_dur);
// TA_BEGIN: cpu4_thread10.c:266 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched20_266_66 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:266 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched20_266_66_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched20_266_66;
time_account("main/pthread_attr_setinheritsched20", __ta_t0_main_pthread_attr_setinheritsched20_266_66_dur);
time_trace("main/pthread_attr_setinheritsched20", __ta_t0_main_pthread_attr_setinheritsched20_266_66, __ta_t0_main_pthread_attr_setinheritsched20_266_66_dur);
// TA_BEGIN: cpu4_thread10.c:267 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy21_267_65 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:267 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy21_267_65_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy21_267_65;
time_account("main/pthread_attr_setschedpolicy21", __ta_t0_main_pthread_attr_setschedpolicy21_267_65_dur);
time_trace("main/pthread_attr_setschedpolicy21", __ta_t0_main_pthread_attr_setschedpolicy21_267_65, __ta_t0_main_pthread_attr_setschedpolicy21_267_65_dur);
// TA_BEGIN: cpu4_thread10.c:268 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset22_268_64 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:268 memset
uint64_t __ta_t0_main_memset22_268_64_dur = now_ns() - __ta_t0_main_memset22_268_64;
time_account("main/memset22", __ta_t0_main_memset22_268_64_dur);
time_trace("main/memset22", __ta_t0_main_memset22_268_64, __ta_t0_main_memset22_268_64_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:270 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam23_270_63 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:270 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam23_270_63_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam23_270_63;
time_account("main/pthread_attr_setschedparam23", __ta_t0_main_pthread_attr_setschedparam23_270_63_dur);
time_trace("main/pthread_attr_setschedparam23", __ta_t0_main_pthread_attr_setschedparam23_270_63, __ta_t0_main_pthread_attr_setschedparam23_270_63_dur);
// TA_BEGIN: cpu4_thread10.c:271 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create24_271_62 = now_ns();
        pthread_create(&t2, &attr, worker2, NULL);
// TA_END: cpu4_thread10.c:271 pthread_create
uint64_t __ta_t0_main_pthread_create24_271_62_dur = now_ns() - __ta_t0_main_pthread_create24_271_62;
time_account("main/pthread_create24", __ta_t0_main_pthread_create24_271_62_dur);
time_trace("main/pthread_create24", __ta_t0_main_pthread_create24_271_62, __ta_t0_main_pthread_create24_271_62_dur);
// TA_BEGIN: cpu4_thread10.c:272 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy25_272_61 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:272 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy25_272_61_dur = now_ns() - __ta_t0_main_pthread_attr_destroy25_272_61;
time_account("main/pthread_attr_destroy25", __ta_t0_main_pthread_attr_destroy25_272_61_dur);
time_trace("main/pthread_attr_destroy25", __ta_t0_main_pthread_attr_destroy25_272_61, __ta_t0_main_pthread_attr_destroy25_272_61_dur);
    }

    /* t3 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:279 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init26_279_60 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:279 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init26_279_60_dur = now_ns() - __ta_t0_main_pthread_attr_init26_279_60;
time_account("main/pthread_attr_init26", __ta_t0_main_pthread_attr_init26_279_60_dur);
time_trace("main/pthread_attr_init26", __ta_t0_main_pthread_attr_init26_279_60, __ta_t0_main_pthread_attr_init26_279_60_dur);
// TA_BEGIN: cpu4_thread10.c:280 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched27_280_59 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:280 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched27_280_59_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched27_280_59;
time_account("main/pthread_attr_setinheritsched27", __ta_t0_main_pthread_attr_setinheritsched27_280_59_dur);
time_trace("main/pthread_attr_setinheritsched27", __ta_t0_main_pthread_attr_setinheritsched27_280_59, __ta_t0_main_pthread_attr_setinheritsched27_280_59_dur);
// TA_BEGIN: cpu4_thread10.c:281 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy28_281_58 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:281 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy28_281_58_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy28_281_58;
time_account("main/pthread_attr_setschedpolicy28", __ta_t0_main_pthread_attr_setschedpolicy28_281_58_dur);
time_trace("main/pthread_attr_setschedpolicy28", __ta_t0_main_pthread_attr_setschedpolicy28_281_58, __ta_t0_main_pthread_attr_setschedpolicy28_281_58_dur);
// TA_BEGIN: cpu4_thread10.c:282 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset29_282_57 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:282 memset
uint64_t __ta_t0_main_memset29_282_57_dur = now_ns() - __ta_t0_main_memset29_282_57;
time_account("main/memset29", __ta_t0_main_memset29_282_57_dur);
time_trace("main/memset29", __ta_t0_main_memset29_282_57, __ta_t0_main_memset29_282_57_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:284 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam30_284_56 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:284 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam30_284_56_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam30_284_56;
time_account("main/pthread_attr_setschedparam30", __ta_t0_main_pthread_attr_setschedparam30_284_56_dur);
time_trace("main/pthread_attr_setschedparam30", __ta_t0_main_pthread_attr_setschedparam30_284_56, __ta_t0_main_pthread_attr_setschedparam30_284_56_dur);
// TA_BEGIN: cpu4_thread10.c:285 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create31_285_55 = now_ns();
        pthread_create(&t3, &attr, worker3, NULL);
// TA_END: cpu4_thread10.c:285 pthread_create
uint64_t __ta_t0_main_pthread_create31_285_55_dur = now_ns() - __ta_t0_main_pthread_create31_285_55;
time_account("main/pthread_create31", __ta_t0_main_pthread_create31_285_55_dur);
time_trace("main/pthread_create31", __ta_t0_main_pthread_create31_285_55, __ta_t0_main_pthread_create31_285_55_dur);
// TA_BEGIN: cpu4_thread10.c:286 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy32_286_54 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:286 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy32_286_54_dur = now_ns() - __ta_t0_main_pthread_attr_destroy32_286_54;
time_account("main/pthread_attr_destroy32", __ta_t0_main_pthread_attr_destroy32_286_54_dur);
time_trace("main/pthread_attr_destroy32", __ta_t0_main_pthread_attr_destroy32_286_54, __ta_t0_main_pthread_attr_destroy32_286_54_dur);
    }

    /* t4 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:293 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init33_293_53 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:293 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init33_293_53_dur = now_ns() - __ta_t0_main_pthread_attr_init33_293_53;
time_account("main/pthread_attr_init33", __ta_t0_main_pthread_attr_init33_293_53_dur);
time_trace("main/pthread_attr_init33", __ta_t0_main_pthread_attr_init33_293_53, __ta_t0_main_pthread_attr_init33_293_53_dur);
// TA_BEGIN: cpu4_thread10.c:294 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched34_294_52 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:294 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched34_294_52_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched34_294_52;
time_account("main/pthread_attr_setinheritsched34", __ta_t0_main_pthread_attr_setinheritsched34_294_52_dur);
time_trace("main/pthread_attr_setinheritsched34", __ta_t0_main_pthread_attr_setinheritsched34_294_52, __ta_t0_main_pthread_attr_setinheritsched34_294_52_dur);
// TA_BEGIN: cpu4_thread10.c:295 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy35_295_51 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:295 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy35_295_51_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy35_295_51;
time_account("main/pthread_attr_setschedpolicy35", __ta_t0_main_pthread_attr_setschedpolicy35_295_51_dur);
time_trace("main/pthread_attr_setschedpolicy35", __ta_t0_main_pthread_attr_setschedpolicy35_295_51, __ta_t0_main_pthread_attr_setschedpolicy35_295_51_dur);
// TA_BEGIN: cpu4_thread10.c:296 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset36_296_50 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:296 memset
uint64_t __ta_t0_main_memset36_296_50_dur = now_ns() - __ta_t0_main_memset36_296_50;
time_account("main/memset36", __ta_t0_main_memset36_296_50_dur);
time_trace("main/memset36", __ta_t0_main_memset36_296_50, __ta_t0_main_memset36_296_50_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:298 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam37_298_49 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:298 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam37_298_49_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam37_298_49;
time_account("main/pthread_attr_setschedparam37", __ta_t0_main_pthread_attr_setschedparam37_298_49_dur);
time_trace("main/pthread_attr_setschedparam37", __ta_t0_main_pthread_attr_setschedparam37_298_49, __ta_t0_main_pthread_attr_setschedparam37_298_49_dur);
// TA_BEGIN: cpu4_thread10.c:299 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create38_299_48 = now_ns();
        pthread_create(&t4, &attr, worker4, NULL);
// TA_END: cpu4_thread10.c:299 pthread_create
uint64_t __ta_t0_main_pthread_create38_299_48_dur = now_ns() - __ta_t0_main_pthread_create38_299_48;
time_account("main/pthread_create38", __ta_t0_main_pthread_create38_299_48_dur);
time_trace("main/pthread_create38", __ta_t0_main_pthread_create38_299_48, __ta_t0_main_pthread_create38_299_48_dur);
// TA_BEGIN: cpu4_thread10.c:300 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy39_300_47 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:300 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy39_300_47_dur = now_ns() - __ta_t0_main_pthread_attr_destroy39_300_47;
time_account("main/pthread_attr_destroy39", __ta_t0_main_pthread_attr_destroy39_300_47_dur);
time_trace("main/pthread_attr_destroy39", __ta_t0_main_pthread_attr_destroy39_300_47, __ta_t0_main_pthread_attr_destroy39_300_47_dur);
    }

    /* t5 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:307 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init40_307_46 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:307 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init40_307_46_dur = now_ns() - __ta_t0_main_pthread_attr_init40_307_46;
time_account("main/pthread_attr_init40", __ta_t0_main_pthread_attr_init40_307_46_dur);
time_trace("main/pthread_attr_init40", __ta_t0_main_pthread_attr_init40_307_46, __ta_t0_main_pthread_attr_init40_307_46_dur);
// TA_BEGIN: cpu4_thread10.c:308 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched41_308_45 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:308 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched41_308_45_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched41_308_45;
time_account("main/pthread_attr_setinheritsched41", __ta_t0_main_pthread_attr_setinheritsched41_308_45_dur);
time_trace("main/pthread_attr_setinheritsched41", __ta_t0_main_pthread_attr_setinheritsched41_308_45, __ta_t0_main_pthread_attr_setinheritsched41_308_45_dur);
// TA_BEGIN: cpu4_thread10.c:309 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy42_309_44 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:309 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy42_309_44_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy42_309_44;
time_account("main/pthread_attr_setschedpolicy42", __ta_t0_main_pthread_attr_setschedpolicy42_309_44_dur);
time_trace("main/pthread_attr_setschedpolicy42", __ta_t0_main_pthread_attr_setschedpolicy42_309_44, __ta_t0_main_pthread_attr_setschedpolicy42_309_44_dur);
// TA_BEGIN: cpu4_thread10.c:310 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset43_310_43 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:310 memset
uint64_t __ta_t0_main_memset43_310_43_dur = now_ns() - __ta_t0_main_memset43_310_43;
time_account("main/memset43", __ta_t0_main_memset43_310_43_dur);
time_trace("main/memset43", __ta_t0_main_memset43_310_43, __ta_t0_main_memset43_310_43_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:312 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam44_312_42 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:312 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam44_312_42_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam44_312_42;
time_account("main/pthread_attr_setschedparam44", __ta_t0_main_pthread_attr_setschedparam44_312_42_dur);
time_trace("main/pthread_attr_setschedparam44", __ta_t0_main_pthread_attr_setschedparam44_312_42, __ta_t0_main_pthread_attr_setschedparam44_312_42_dur);
// TA_BEGIN: cpu4_thread10.c:313 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create45_313_41 = now_ns();
        pthread_create(&t5, &attr, worker5, NULL);
// TA_END: cpu4_thread10.c:313 pthread_create
uint64_t __ta_t0_main_pthread_create45_313_41_dur = now_ns() - __ta_t0_main_pthread_create45_313_41;
time_account("main/pthread_create45", __ta_t0_main_pthread_create45_313_41_dur);
time_trace("main/pthread_create45", __ta_t0_main_pthread_create45_313_41, __ta_t0_main_pthread_create45_313_41_dur);
// TA_BEGIN: cpu4_thread10.c:314 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy46_314_40 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:314 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy46_314_40_dur = now_ns() - __ta_t0_main_pthread_attr_destroy46_314_40;
time_account("main/pthread_attr_destroy46", __ta_t0_main_pthread_attr_destroy46_314_40_dur);
time_trace("main/pthread_attr_destroy46", __ta_t0_main_pthread_attr_destroy46_314_40, __ta_t0_main_pthread_attr_destroy46_314_40_dur);
    }

    /* t6 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:321 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init47_321_39 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:321 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init47_321_39_dur = now_ns() - __ta_t0_main_pthread_attr_init47_321_39;
time_account("main/pthread_attr_init47", __ta_t0_main_pthread_attr_init47_321_39_dur);
time_trace("main/pthread_attr_init47", __ta_t0_main_pthread_attr_init47_321_39, __ta_t0_main_pthread_attr_init47_321_39_dur);
// TA_BEGIN: cpu4_thread10.c:322 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched48_322_38 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:322 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched48_322_38_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched48_322_38;
time_account("main/pthread_attr_setinheritsched48", __ta_t0_main_pthread_attr_setinheritsched48_322_38_dur);
time_trace("main/pthread_attr_setinheritsched48", __ta_t0_main_pthread_attr_setinheritsched48_322_38, __ta_t0_main_pthread_attr_setinheritsched48_322_38_dur);
// TA_BEGIN: cpu4_thread10.c:323 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy49_323_37 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:323 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy49_323_37_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy49_323_37;
time_account("main/pthread_attr_setschedpolicy49", __ta_t0_main_pthread_attr_setschedpolicy49_323_37_dur);
time_trace("main/pthread_attr_setschedpolicy49", __ta_t0_main_pthread_attr_setschedpolicy49_323_37, __ta_t0_main_pthread_attr_setschedpolicy49_323_37_dur);
// TA_BEGIN: cpu4_thread10.c:324 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset50_324_36 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:324 memset
uint64_t __ta_t0_main_memset50_324_36_dur = now_ns() - __ta_t0_main_memset50_324_36;
time_account("main/memset50", __ta_t0_main_memset50_324_36_dur);
time_trace("main/memset50", __ta_t0_main_memset50_324_36, __ta_t0_main_memset50_324_36_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:326 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam51_326_35 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:326 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam51_326_35_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam51_326_35;
time_account("main/pthread_attr_setschedparam51", __ta_t0_main_pthread_attr_setschedparam51_326_35_dur);
time_trace("main/pthread_attr_setschedparam51", __ta_t0_main_pthread_attr_setschedparam51_326_35, __ta_t0_main_pthread_attr_setschedparam51_326_35_dur);
// TA_BEGIN: cpu4_thread10.c:327 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create52_327_34 = now_ns();
        pthread_create(&t6, &attr, worker6, NULL);
// TA_END: cpu4_thread10.c:327 pthread_create
uint64_t __ta_t0_main_pthread_create52_327_34_dur = now_ns() - __ta_t0_main_pthread_create52_327_34;
time_account("main/pthread_create52", __ta_t0_main_pthread_create52_327_34_dur);
time_trace("main/pthread_create52", __ta_t0_main_pthread_create52_327_34, __ta_t0_main_pthread_create52_327_34_dur);
// TA_BEGIN: cpu4_thread10.c:328 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy53_328_33 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:328 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy53_328_33_dur = now_ns() - __ta_t0_main_pthread_attr_destroy53_328_33;
time_account("main/pthread_attr_destroy53", __ta_t0_main_pthread_attr_destroy53_328_33_dur);
time_trace("main/pthread_attr_destroy53", __ta_t0_main_pthread_attr_destroy53_328_33, __ta_t0_main_pthread_attr_destroy53_328_33_dur);
    }

    /* t7 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:335 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init54_335_32 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:335 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init54_335_32_dur = now_ns() - __ta_t0_main_pthread_attr_init54_335_32;
time_account("main/pthread_attr_init54", __ta_t0_main_pthread_attr_init54_335_32_dur);
time_trace("main/pthread_attr_init54", __ta_t0_main_pthread_attr_init54_335_32, __ta_t0_main_pthread_attr_init54_335_32_dur);
// TA_BEGIN: cpu4_thread10.c:336 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched55_336_31 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:336 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched55_336_31_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched55_336_31;
time_account("main/pthread_attr_setinheritsched55", __ta_t0_main_pthread_attr_setinheritsched55_336_31_dur);
time_trace("main/pthread_attr_setinheritsched55", __ta_t0_main_pthread_attr_setinheritsched55_336_31, __ta_t0_main_pthread_attr_setinheritsched55_336_31_dur);
// TA_BEGIN: cpu4_thread10.c:337 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy56_337_30 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:337 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy56_337_30_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy56_337_30;
time_account("main/pthread_attr_setschedpolicy56", __ta_t0_main_pthread_attr_setschedpolicy56_337_30_dur);
time_trace("main/pthread_attr_setschedpolicy56", __ta_t0_main_pthread_attr_setschedpolicy56_337_30, __ta_t0_main_pthread_attr_setschedpolicy56_337_30_dur);
// TA_BEGIN: cpu4_thread10.c:338 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset57_338_29 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:338 memset
uint64_t __ta_t0_main_memset57_338_29_dur = now_ns() - __ta_t0_main_memset57_338_29;
time_account("main/memset57", __ta_t0_main_memset57_338_29_dur);
time_trace("main/memset57", __ta_t0_main_memset57_338_29, __ta_t0_main_memset57_338_29_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:340 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam58_340_28 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:340 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam58_340_28_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam58_340_28;
time_account("main/pthread_attr_setschedparam58", __ta_t0_main_pthread_attr_setschedparam58_340_28_dur);
time_trace("main/pthread_attr_setschedparam58", __ta_t0_main_pthread_attr_setschedparam58_340_28, __ta_t0_main_pthread_attr_setschedparam58_340_28_dur);
// TA_BEGIN: cpu4_thread10.c:341 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create59_341_27 = now_ns();
        pthread_create(&t7, &attr, worker7, NULL);
// TA_END: cpu4_thread10.c:341 pthread_create
uint64_t __ta_t0_main_pthread_create59_341_27_dur = now_ns() - __ta_t0_main_pthread_create59_341_27;
time_account("main/pthread_create59", __ta_t0_main_pthread_create59_341_27_dur);
time_trace("main/pthread_create59", __ta_t0_main_pthread_create59_341_27, __ta_t0_main_pthread_create59_341_27_dur);
// TA_BEGIN: cpu4_thread10.c:342 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy60_342_26 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:342 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy60_342_26_dur = now_ns() - __ta_t0_main_pthread_attr_destroy60_342_26;
time_account("main/pthread_attr_destroy60", __ta_t0_main_pthread_attr_destroy60_342_26_dur);
time_trace("main/pthread_attr_destroy60", __ta_t0_main_pthread_attr_destroy60_342_26, __ta_t0_main_pthread_attr_destroy60_342_26_dur);
    }

    /* t8 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:349 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init61_349_25 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:349 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init61_349_25_dur = now_ns() - __ta_t0_main_pthread_attr_init61_349_25;
time_account("main/pthread_attr_init61", __ta_t0_main_pthread_attr_init61_349_25_dur);
time_trace("main/pthread_attr_init61", __ta_t0_main_pthread_attr_init61_349_25, __ta_t0_main_pthread_attr_init61_349_25_dur);
// TA_BEGIN: cpu4_thread10.c:350 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched62_350_24 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:350 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched62_350_24_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched62_350_24;
time_account("main/pthread_attr_setinheritsched62", __ta_t0_main_pthread_attr_setinheritsched62_350_24_dur);
time_trace("main/pthread_attr_setinheritsched62", __ta_t0_main_pthread_attr_setinheritsched62_350_24, __ta_t0_main_pthread_attr_setinheritsched62_350_24_dur);
// TA_BEGIN: cpu4_thread10.c:351 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy63_351_23 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:351 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy63_351_23_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy63_351_23;
time_account("main/pthread_attr_setschedpolicy63", __ta_t0_main_pthread_attr_setschedpolicy63_351_23_dur);
time_trace("main/pthread_attr_setschedpolicy63", __ta_t0_main_pthread_attr_setschedpolicy63_351_23, __ta_t0_main_pthread_attr_setschedpolicy63_351_23_dur);
// TA_BEGIN: cpu4_thread10.c:352 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset64_352_22 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:352 memset
uint64_t __ta_t0_main_memset64_352_22_dur = now_ns() - __ta_t0_main_memset64_352_22;
time_account("main/memset64", __ta_t0_main_memset64_352_22_dur);
time_trace("main/memset64", __ta_t0_main_memset64_352_22, __ta_t0_main_memset64_352_22_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:354 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam65_354_21 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:354 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam65_354_21_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam65_354_21;
time_account("main/pthread_attr_setschedparam65", __ta_t0_main_pthread_attr_setschedparam65_354_21_dur);
time_trace("main/pthread_attr_setschedparam65", __ta_t0_main_pthread_attr_setschedparam65_354_21, __ta_t0_main_pthread_attr_setschedparam65_354_21_dur);
// TA_BEGIN: cpu4_thread10.c:355 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create66_355_20 = now_ns();
        pthread_create(&t8, &attr, worker8, NULL);
// TA_END: cpu4_thread10.c:355 pthread_create
uint64_t __ta_t0_main_pthread_create66_355_20_dur = now_ns() - __ta_t0_main_pthread_create66_355_20;
time_account("main/pthread_create66", __ta_t0_main_pthread_create66_355_20_dur);
time_trace("main/pthread_create66", __ta_t0_main_pthread_create66_355_20, __ta_t0_main_pthread_create66_355_20_dur);
// TA_BEGIN: cpu4_thread10.c:356 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy67_356_19 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:356 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy67_356_19_dur = now_ns() - __ta_t0_main_pthread_attr_destroy67_356_19;
time_account("main/pthread_attr_destroy67", __ta_t0_main_pthread_attr_destroy67_356_19_dur);
time_trace("main/pthread_attr_destroy67", __ta_t0_main_pthread_attr_destroy67_356_19, __ta_t0_main_pthread_attr_destroy67_356_19_dur);
    }

    /* t9 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
// TA_BEGIN: cpu4_thread10.c:363 pthread_attr_init
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_init68_363_18 = now_ns();
        pthread_attr_init(&attr);
// TA_END: cpu4_thread10.c:363 pthread_attr_init
uint64_t __ta_t0_main_pthread_attr_init68_363_18_dur = now_ns() - __ta_t0_main_pthread_attr_init68_363_18;
time_account("main/pthread_attr_init68", __ta_t0_main_pthread_attr_init68_363_18_dur);
time_trace("main/pthread_attr_init68", __ta_t0_main_pthread_attr_init68_363_18, __ta_t0_main_pthread_attr_init68_363_18_dur);
// TA_BEGIN: cpu4_thread10.c:364 pthread_attr_setinheritsched
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setinheritsched69_364_17 = now_ns();
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
// TA_END: cpu4_thread10.c:364 pthread_attr_setinheritsched
uint64_t __ta_t0_main_pthread_attr_setinheritsched69_364_17_dur = now_ns() - __ta_t0_main_pthread_attr_setinheritsched69_364_17;
time_account("main/pthread_attr_setinheritsched69", __ta_t0_main_pthread_attr_setinheritsched69_364_17_dur);
time_trace("main/pthread_attr_setinheritsched69", __ta_t0_main_pthread_attr_setinheritsched69_364_17, __ta_t0_main_pthread_attr_setinheritsched69_364_17_dur);
// TA_BEGIN: cpu4_thread10.c:365 pthread_attr_setschedpolicy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedpolicy70_365_16 = now_ns();
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
// TA_END: cpu4_thread10.c:365 pthread_attr_setschedpolicy
uint64_t __ta_t0_main_pthread_attr_setschedpolicy70_365_16_dur = now_ns() - __ta_t0_main_pthread_attr_setschedpolicy70_365_16;
time_account("main/pthread_attr_setschedpolicy70", __ta_t0_main_pthread_attr_setschedpolicy70_365_16_dur);
time_trace("main/pthread_attr_setschedpolicy70", __ta_t0_main_pthread_attr_setschedpolicy70_365_16, __ta_t0_main_pthread_attr_setschedpolicy70_365_16_dur);
// TA_BEGIN: cpu4_thread10.c:366 memset
; /* TA_PAD */
uint64_t __ta_t0_main_memset71_366_15 = now_ns();
        memset(&sp, 0, sizeof(sp));
// TA_END: cpu4_thread10.c:366 memset
uint64_t __ta_t0_main_memset71_366_15_dur = now_ns() - __ta_t0_main_memset71_366_15;
time_account("main/memset71", __ta_t0_main_memset71_366_15_dur);
time_trace("main/memset71", __ta_t0_main_memset71_366_15, __ta_t0_main_memset71_366_15_dur);
        sp.sched_priority = prio;
// TA_BEGIN: cpu4_thread10.c:368 pthread_attr_setschedparam
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_setschedparam72_368_14 = now_ns();
        pthread_attr_setschedparam(&attr, &sp);
// TA_END: cpu4_thread10.c:368 pthread_attr_setschedparam
uint64_t __ta_t0_main_pthread_attr_setschedparam72_368_14_dur = now_ns() - __ta_t0_main_pthread_attr_setschedparam72_368_14;
time_account("main/pthread_attr_setschedparam72", __ta_t0_main_pthread_attr_setschedparam72_368_14_dur);
time_trace("main/pthread_attr_setschedparam72", __ta_t0_main_pthread_attr_setschedparam72_368_14, __ta_t0_main_pthread_attr_setschedparam72_368_14_dur);
// TA_BEGIN: cpu4_thread10.c:369 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create73_369_13 = now_ns();
        pthread_create(&t9, &attr, worker9, NULL);
// TA_END: cpu4_thread10.c:369 pthread_create
uint64_t __ta_t0_main_pthread_create73_369_13_dur = now_ns() - __ta_t0_main_pthread_create73_369_13;
time_account("main/pthread_create73", __ta_t0_main_pthread_create73_369_13_dur);
time_trace("main/pthread_create73", __ta_t0_main_pthread_create73_369_13, __ta_t0_main_pthread_create73_369_13_dur);
// TA_BEGIN: cpu4_thread10.c:370 pthread_attr_destroy
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_attr_destroy74_370_12 = now_ns();
        pthread_attr_destroy(&attr);
// TA_END: cpu4_thread10.c:370 pthread_attr_destroy
uint64_t __ta_t0_main_pthread_attr_destroy74_370_12_dur = now_ns() - __ta_t0_main_pthread_attr_destroy74_370_12;
time_account("main/pthread_attr_destroy74", __ta_t0_main_pthread_attr_destroy74_370_12_dur);
time_trace("main/pthread_attr_destroy74", __ta_t0_main_pthread_attr_destroy74_370_12, __ta_t0_main_pthread_attr_destroy74_370_12_dur);
    }

// TA_BEGIN: cpu4_thread10.c:373 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join75_373_11 = now_ns();
    pthread_join(t0, NULL);
// TA_END: cpu4_thread10.c:373 pthread_join
uint64_t __ta_t0_main_pthread_join75_373_11_dur = now_ns() - __ta_t0_main_pthread_join75_373_11;
time_account("main/pthread_join75", __ta_t0_main_pthread_join75_373_11_dur);
time_trace("main/pthread_join75", __ta_t0_main_pthread_join75_373_11, __ta_t0_main_pthread_join75_373_11_dur);
// TA_BEGIN: cpu4_thread10.c:374 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join76_374_10 = now_ns();
    pthread_join(t1, NULL);
// TA_END: cpu4_thread10.c:374 pthread_join
uint64_t __ta_t0_main_pthread_join76_374_10_dur = now_ns() - __ta_t0_main_pthread_join76_374_10;
time_account("main/pthread_join76", __ta_t0_main_pthread_join76_374_10_dur);
time_trace("main/pthread_join76", __ta_t0_main_pthread_join76_374_10, __ta_t0_main_pthread_join76_374_10_dur);
// TA_BEGIN: cpu4_thread10.c:375 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join77_375_9 = now_ns();
    pthread_join(t2, NULL);
// TA_END: cpu4_thread10.c:375 pthread_join
uint64_t __ta_t0_main_pthread_join77_375_9_dur = now_ns() - __ta_t0_main_pthread_join77_375_9;
time_account("main/pthread_join77", __ta_t0_main_pthread_join77_375_9_dur);
time_trace("main/pthread_join77", __ta_t0_main_pthread_join77_375_9, __ta_t0_main_pthread_join77_375_9_dur);
// TA_BEGIN: cpu4_thread10.c:376 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join78_376_8 = now_ns();
    pthread_join(t3, NULL);
// TA_END: cpu4_thread10.c:376 pthread_join
uint64_t __ta_t0_main_pthread_join78_376_8_dur = now_ns() - __ta_t0_main_pthread_join78_376_8;
time_account("main/pthread_join78", __ta_t0_main_pthread_join78_376_8_dur);
time_trace("main/pthread_join78", __ta_t0_main_pthread_join78_376_8, __ta_t0_main_pthread_join78_376_8_dur);
// TA_BEGIN: cpu4_thread10.c:377 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join79_377_7 = now_ns();
    pthread_join(t4, NULL);
// TA_END: cpu4_thread10.c:377 pthread_join
uint64_t __ta_t0_main_pthread_join79_377_7_dur = now_ns() - __ta_t0_main_pthread_join79_377_7;
time_account("main/pthread_join79", __ta_t0_main_pthread_join79_377_7_dur);
time_trace("main/pthread_join79", __ta_t0_main_pthread_join79_377_7, __ta_t0_main_pthread_join79_377_7_dur);
// TA_BEGIN: cpu4_thread10.c:378 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join80_378_6 = now_ns();
    pthread_join(t5, NULL);
// TA_END: cpu4_thread10.c:378 pthread_join
uint64_t __ta_t0_main_pthread_join80_378_6_dur = now_ns() - __ta_t0_main_pthread_join80_378_6;
time_account("main/pthread_join80", __ta_t0_main_pthread_join80_378_6_dur);
time_trace("main/pthread_join80", __ta_t0_main_pthread_join80_378_6, __ta_t0_main_pthread_join80_378_6_dur);
// TA_BEGIN: cpu4_thread10.c:379 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join81_379_5 = now_ns();
    pthread_join(t6, NULL);
// TA_END: cpu4_thread10.c:379 pthread_join
uint64_t __ta_t0_main_pthread_join81_379_5_dur = now_ns() - __ta_t0_main_pthread_join81_379_5;
time_account("main/pthread_join81", __ta_t0_main_pthread_join81_379_5_dur);
time_trace("main/pthread_join81", __ta_t0_main_pthread_join81_379_5, __ta_t0_main_pthread_join81_379_5_dur);
// TA_BEGIN: cpu4_thread10.c:380 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join82_380_4 = now_ns();
    pthread_join(t7, NULL);
// TA_END: cpu4_thread10.c:380 pthread_join
uint64_t __ta_t0_main_pthread_join82_380_4_dur = now_ns() - __ta_t0_main_pthread_join82_380_4;
time_account("main/pthread_join82", __ta_t0_main_pthread_join82_380_4_dur);
time_trace("main/pthread_join82", __ta_t0_main_pthread_join82_380_4, __ta_t0_main_pthread_join82_380_4_dur);
// TA_BEGIN: cpu4_thread10.c:381 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join83_381_3 = now_ns();
    pthread_join(t8, NULL);
// TA_END: cpu4_thread10.c:381 pthread_join
uint64_t __ta_t0_main_pthread_join83_381_3_dur = now_ns() - __ta_t0_main_pthread_join83_381_3;
time_account("main/pthread_join83", __ta_t0_main_pthread_join83_381_3_dur);
time_trace("main/pthread_join83", __ta_t0_main_pthread_join83_381_3, __ta_t0_main_pthread_join83_381_3_dur);
// TA_BEGIN: cpu4_thread10.c:382 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join84_382_2 = now_ns();
    pthread_join(t9, NULL);
// TA_END: cpu4_thread10.c:382 pthread_join
uint64_t __ta_t0_main_pthread_join84_382_2_dur = now_ns() - __ta_t0_main_pthread_join84_382_2;
time_account("main/pthread_join84", __ta_t0_main_pthread_join84_382_2_dur);
time_trace("main/pthread_join84", __ta_t0_main_pthread_join84_382_2, __ta_t0_main_pthread_join84_382_2_dur);

// TA_BEGIN: cpu4_thread10.c:384 printf
; /* TA_PAD */
uint64_t __ta_t0_main_printf85_384_1 = now_ns();
    printf("done. sample=%f\n", C[0][0]);
// TA_END: cpu4_thread10.c:384 printf
uint64_t __ta_t0_main_printf85_384_1_dur = now_ns() - __ta_t0_main_printf85_384_1;
time_account("main/printf85", __ta_t0_main_printf85_384_1_dur);
time_trace("main/printf85", __ta_t0_main_printf85_384_1, __ta_t0_main_printf85_384_1_dur);
    return 0;
}
