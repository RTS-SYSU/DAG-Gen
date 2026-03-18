#define _GNU_SOURCE
#include "segtrace.h"
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>

/* 4 核、16 线程；强关键链 + 填充任务：
 * 关键链：c0(25s)->c1(22s)->c2(20s)->c3(18s)->c4(16s)
 * 填充：f0..f10（各 5.0s），f11（3.0s）
 * 耗时按 0.1x 缩放执行。父线程仅创建下一个链节点，不内部 join；所有 join 放 main。
 */

// Design goal (experiment2): make FIFO baseline significantly worse than LPF-priority run.
// Only allowed knobs: add/remove threads and adjust per-thread work weights.
// Strategy: increase filler weights so they contend long enough to slow the critical chain in baseline,
// while keeping the critical chain slightly longer than the filler group under LPF.
#define C0 30.0
#define C1 27.0
#define C2 24.0
#define C3 21.0
#define C4 18.0
#define F_LONG 28.0
#define F_SHORT 20.0

static void *c0_fn(void *arg);
static void *c1_fn(void *arg);
static void *c2_fn(void *arg);
static void *c3_fn(void *arg);
static void *c4_fn(void *arg);
static void *f0_fn(void *arg);
static void *f1_fn(void *arg);
static void *f2_fn(void *arg);
static void *f3_fn(void *arg);
static void *f4_fn(void *arg);
static void *f5_fn(void *arg);
static void *f6_fn(void *arg);
static void *f7_fn(void *arg);
static void *f8_fn(void *arg);
static void *f9_fn(void *arg);
static void *f10_fn(void *arg);
static void *f11_fn(void *arg);

#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 25000
#endif

static double A[MAT_N][MAT_N];
static double B[MAT_N][MAT_N];
static double C[MAT_N][MAT_N];

static pthread_t tc0, tc1, tc2, tc3, tc4;
static pthread_t tf0, tf1, tf2, tf3, tf4, tf5, tf6, tf7, tf8, tf9, tf10, tf11;

static void init_matrices(void)
{
    for (int i = 0; i < MAT_N; ++i) {
        for (int j = 0; j < MAT_N; ++j) {
            A[i][j] = (double)(i + j + 1);
            B[i][j] = (double)(i * 2 + j + 3);
            C[i][j] = 0.0;
        }
    }
}

static void busy_wait_seconds(double seconds)
{
    int repeat = (int)(seconds * WORK_SCALE * 0.1);
    if (repeat < 1) repeat = 1;
    for (int r = 0; r < repeat; ++r) {
        for (int i = 0; i < MAT_N; ++i) {
            for (int j = 0; j < MAT_N; ++j) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; ++k) {
                    acc += A[i][k] * B[k][j];
                }
                C[i][j] = acc;
            }
        }
    }
}

static struct timespec g_prog_start;

static void *c4_fn(void *arg)
{
SEG_BEGIN("SEG:c4_fn#001@90-91");
    (void)arg;
    busy_wait_seconds(C4);
SEG_END("SEG:c4_fn#001@90-91");
    return NULL;
}

static void *c3_fn(void *arg)
{
SEG_BEGIN("SEG:c3_fn#001@97-98");
    busy_wait_seconds(C3);
    pthread_create(&tc4, NULL, c4_fn, NULL);
SEG_END("SEG:c3_fn#001@97-98");
    return NULL;
}

static void *c2_fn(void *arg)
{

SEG_BEGIN("SEG:c2_fn#001@105-106");
    busy_wait_seconds(C2);
    pthread_create(&tc3, NULL, c3_fn, NULL);
SEG_END("SEG:c2_fn#001@105-106");
    return NULL;
}

static void *c1_fn(void *arg)
{
SEG_BEGIN("SEG:c1_fn#001@112-113");
    busy_wait_seconds(C1);
    pthread_create(&tc2, NULL, c2_fn, NULL);
SEG_END("SEG:c1_fn#001@112-113");
    return NULL;
}

static void *c0_fn(void *arg)
{
SEG_BEGIN("SEG:c0_fn#001@119-120");
    busy_wait_seconds(C0);
    pthread_create(&tc1, NULL, c1_fn, NULL);
SEG_END("SEG:c0_fn#001@119-120");
    return NULL;
}

static void *f0_fn(void *arg)
{
SEG_BEGIN("SEG:f0_fn#001@126-126");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f0_fn#001@126-126");
    return NULL;
}

static void *f1_fn(void *arg)
{
SEG_BEGIN("SEG:f1_fn#001@132-132");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f1_fn#001@132-132");
    return NULL;
}

static void *f2_fn(void *arg)
{

SEG_BEGIN("SEG:f2_fn#001@139-139");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f2_fn#001@139-139");
    return NULL;
}

static void *f3_fn(void *arg)
{
SEG_BEGIN("SEG:f3_fn#001@145-145");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f3_fn#001@145-145");
    return NULL;
}

static void *f4_fn(void *arg)
{
SEG_BEGIN("SEG:f4_fn#001@151-151");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f4_fn#001@151-151");
    return NULL;
}

static void *f5_fn(void *arg)
{
SEG_BEGIN("SEG:f5_fn#001@157-157");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f5_fn#001@157-157");
    return NULL;
}

static void *f6_fn(void *arg)
{
SEG_BEGIN("SEG:f6_fn#001@163-163");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f6_fn#001@163-163");
    return NULL;
}

static void *f7_fn(void *arg)
{
SEG_BEGIN("SEG:f7_fn#001@169-169");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f7_fn#001@169-169");
    return NULL;
}

static void *f8_fn(void *arg)
{
SEG_BEGIN("SEG:f8_fn#001@175-175");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f8_fn#001@175-175");
    return NULL;
}

static void *f9_fn(void *arg)
{
SEG_BEGIN("SEG:f9_fn#001@181-181");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f9_fn#001@181-181");
    return NULL;
}

static void *f10_fn(void *arg)
{
SEG_BEGIN("SEG:f10_fn#001@187-187");
    busy_wait_seconds(F_LONG);
SEG_END("SEG:f10_fn#001@187-187");
    return NULL;
}

static void *f11_fn(void *arg)
{
SEG_BEGIN("SEG:f11_fn#001@193-193");
    busy_wait_seconds(F_SHORT);
SEG_END("SEG:f11_fn#001@193-193");
    return NULL;
}

int main(void)
{
SEG_BEGIN("SEG:main#001@199-216");
    struct timespec ts_prog_start, ts_prog_end;
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    CPU_SET(1, &set);
    CPU_SET(2, &set);
    CPU_SET(3, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0) {
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
    }

    init_matrices();
    clock_gettime(CLOCK_MONOTONIC, &g_prog_start);
    clock_gettime(CLOCK_MONOTONIC, &ts_prog_start);

    /* 启动关键链入口 + 填充任务 */
    /* 先创建填充任务，再创建关键链入口，便于 FIFO 先跑填充 */
    pthread_create(&tf0, NULL, f0_fn, NULL);
SEG_END("SEG:main#001@199-216");
SEG_BEGIN("SEG:main#002@217-217");
    pthread_create(&tf1, NULL, f1_fn, NULL);
SEG_END("SEG:main#002@217-217");
SEG_BEGIN("SEG:main#003@218-218");
    pthread_create(&tf2, NULL, f2_fn, NULL);
SEG_END("SEG:main#003@218-218");
SEG_BEGIN("SEG:main#004@219-219");
    pthread_create(&tf3, NULL, f3_fn, NULL);
SEG_END("SEG:main#004@219-219");
SEG_BEGIN("SEG:main#005@220-220");
    pthread_create(&tf4, NULL, f4_fn, NULL);
SEG_END("SEG:main#005@220-220");
SEG_BEGIN("SEG:main#006@221-221");
    pthread_create(&tf5, NULL, f5_fn, NULL);
SEG_END("SEG:main#006@221-221");
SEG_BEGIN("SEG:main#007@222-222");
    pthread_create(&tf6, NULL, f6_fn, NULL);
SEG_END("SEG:main#007@222-222");
SEG_BEGIN("SEG:main#008@223-223");
    pthread_create(&tf7, NULL, f7_fn, NULL);
SEG_END("SEG:main#008@223-223");
SEG_BEGIN("SEG:main#009@224-224");
    pthread_create(&tf8, NULL, f8_fn, NULL);
SEG_END("SEG:main#009@224-224");
SEG_BEGIN("SEG:main#010@225-225");
    pthread_create(&tf9, NULL, f9_fn, NULL);
SEG_END("SEG:main#010@225-225");
SEG_BEGIN("SEG:main#011@226-226");
    pthread_create(&tf10, NULL, f10_fn, NULL);
SEG_END("SEG:main#011@226-226");
SEG_BEGIN("SEG:main#012@227-227");
    pthread_create(&tf11, NULL, f11_fn, NULL);
SEG_END("SEG:main#012@227-227");
SEG_BEGIN("SEG:main#013@228-228");
    pthread_create(&tc0, NULL, c0_fn, NULL);
SEG_END("SEG:main#013@228-228");
SEG_BEGIN("SEG:main#014@229-229");
    pthread_join(tc0, NULL);
SEG_END("SEG:main#014@229-229");
SEG_BEGIN("SEG:main#015@230-230");
    pthread_join(tc1, NULL);
SEG_END("SEG:main#015@230-230");
SEG_BEGIN("SEG:main#016@231-231");
    pthread_join(tc2, NULL);
SEG_END("SEG:main#016@231-231");
SEG_BEGIN("SEG:main#017@232-232");
    pthread_join(tc3, NULL);
SEG_END("SEG:main#017@232-232");
SEG_BEGIN("SEG:main#018@233-233");
    pthread_join(tc4, NULL);
SEG_END("SEG:main#018@233-233");
SEG_BEGIN("SEG:main#019@234-234");
    pthread_join(tf0, NULL);
SEG_END("SEG:main#019@234-234");
SEG_BEGIN("SEG:main#020@235-235");
    pthread_join(tf1, NULL);
SEG_END("SEG:main#020@235-235");
SEG_BEGIN("SEG:main#021@236-236");
    pthread_join(tf2, NULL);
SEG_END("SEG:main#021@236-236");
SEG_BEGIN("SEG:main#022@237-237");
    pthread_join(tf3, NULL);
SEG_END("SEG:main#022@237-237");
SEG_BEGIN("SEG:main#023@238-238");
    pthread_join(tf4, NULL);
SEG_END("SEG:main#023@238-238");
SEG_BEGIN("SEG:main#024@239-239");
    pthread_join(tf5, NULL);
SEG_END("SEG:main#024@239-239");
SEG_BEGIN("SEG:main#025@240-240");
    pthread_join(tf6, NULL);
SEG_END("SEG:main#025@240-240");
SEG_BEGIN("SEG:main#026@241-241");
    pthread_join(tf7, NULL);
SEG_END("SEG:main#026@241-241");
SEG_BEGIN("SEG:main#027@242-242");
    pthread_join(tf8, NULL);
SEG_END("SEG:main#027@242-242");
SEG_BEGIN("SEG:main#028@243-243");
    pthread_join(tf9, NULL);
SEG_END("SEG:main#028@243-243");
SEG_BEGIN("SEG:main#029@244-244");
    pthread_join(tf10, NULL);
SEG_END("SEG:main#029@244-244");
SEG_BEGIN("SEG:main#030@245-245");
    pthread_join(tf11, NULL);
SEG_END("SEG:main#030@245-245");
    return 0;
}
