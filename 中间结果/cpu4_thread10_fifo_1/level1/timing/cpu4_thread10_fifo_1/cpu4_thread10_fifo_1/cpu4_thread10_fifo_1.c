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

#define C0 25.0
#define C1 22.0
#define C2 20.0
#define C3 18.0
#define C4 16.0
#define F_LONG 5.0
#define F_SHORT 3.0

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
SEG_BEGIN("THR:c4_fn#001@86-88");
    (void)arg;
    busy_wait_seconds(C4);
    return NULL;
SEG_END("THR:c4_fn#001@86-88");
}

static void *c3_fn(void *arg)
{
SEG_BEGIN("THR:c3_fn#001@93-93");
    busy_wait_seconds(C3);
SEG_END("THR:c3_fn#001@93-93");
SEG_BEGIN("CRT:c3_fn#002@L94");
    pthread_create(&tc4, NULL, c4_fn, NULL);
SEG_END("CRT:c3_fn#002@L94");
SEG_BEGIN("THR:c3_fn#003@95-95");
    return NULL;
SEG_END("THR:c3_fn#003@95-95");
}

static void *c2_fn(void *arg)
{

SEG_BEGIN("THR:c2_fn#001@101-101");
    busy_wait_seconds(C2);
SEG_END("THR:c2_fn#001@101-101");
SEG_BEGIN("CRT:c2_fn#002@L102");
    pthread_create(&tc3, NULL, c3_fn, NULL);
SEG_END("CRT:c2_fn#002@L102");
SEG_BEGIN("THR:c2_fn#003@103-103");
    return NULL;
SEG_END("THR:c2_fn#003@103-103");
}

static void *c1_fn(void *arg)
{
SEG_BEGIN("THR:c1_fn#001@108-108");
    busy_wait_seconds(C1);
SEG_END("THR:c1_fn#001@108-108");
SEG_BEGIN("CRT:c1_fn#002@L109");
    pthread_create(&tc2, NULL, c2_fn, NULL);
SEG_END("CRT:c1_fn#002@L109");
SEG_BEGIN("THR:c1_fn#003@110-110");
    return NULL;
SEG_END("THR:c1_fn#003@110-110");
}

static void *c0_fn(void *arg)
{
SEG_BEGIN("THR:c0_fn#001@115-115");
    busy_wait_seconds(C0);
SEG_END("THR:c0_fn#001@115-115");
SEG_BEGIN("CRT:c0_fn#002@L116");
    pthread_create(&tc1, NULL, c1_fn, NULL);
SEG_END("CRT:c0_fn#002@L116");
SEG_BEGIN("THR:c0_fn#003@117-117");
    return NULL;
SEG_END("THR:c0_fn#003@117-117");
}

static void *f0_fn(void *arg)
{
SEG_BEGIN("THR:f0_fn#001@122-123");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f0_fn#001@122-123");
}

static void *f1_fn(void *arg)
{
SEG_BEGIN("THR:f1_fn#001@128-129");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f1_fn#001@128-129");
}

static void *f2_fn(void *arg)
{

SEG_BEGIN("THR:f2_fn#001@135-136");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f2_fn#001@135-136");
}

static void *f3_fn(void *arg)
{
SEG_BEGIN("THR:f3_fn#001@141-142");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f3_fn#001@141-142");
}

static void *f4_fn(void *arg)
{
SEG_BEGIN("THR:f4_fn#001@147-148");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f4_fn#001@147-148");
}

static void *f5_fn(void *arg)
{
SEG_BEGIN("THR:f5_fn#001@153-154");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f5_fn#001@153-154");
}

static void *f6_fn(void *arg)
{
SEG_BEGIN("THR:f6_fn#001@159-160");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f6_fn#001@159-160");
}

static void *f7_fn(void *arg)
{
SEG_BEGIN("THR:f7_fn#001@165-166");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f7_fn#001@165-166");
}

static void *f8_fn(void *arg)
{
SEG_BEGIN("THR:f8_fn#001@171-172");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f8_fn#001@171-172");
}

static void *f9_fn(void *arg)
{
SEG_BEGIN("THR:f9_fn#001@177-178");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f9_fn#001@177-178");
}

static void *f10_fn(void *arg)
{
SEG_BEGIN("THR:f10_fn#001@183-184");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f10_fn#001@183-184");
}

static void *f11_fn(void *arg)
{
SEG_BEGIN("THR:f11_fn#001@189-190");
    busy_wait_seconds(F_LONG);
    return NULL;
SEG_END("THR:f11_fn#001@189-190");
}

int main(void)
{
SEG_BEGIN("THR:main#001@195-211");
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
SEG_END("THR:main#001@195-211");
SEG_BEGIN("CRT:main#002@L212");
    pthread_create(&tf0, NULL, f0_fn, NULL);
SEG_END("CRT:main#002@L212");
SEG_BEGIN("CRT:main#003@L213");
    pthread_create(&tf1, NULL, f1_fn, NULL);
SEG_END("CRT:main#003@L213");
SEG_BEGIN("CRT:main#004@L214");
    pthread_create(&tf2, NULL, f2_fn, NULL);
SEG_END("CRT:main#004@L214");
SEG_BEGIN("CRT:main#005@L215");
    pthread_create(&tf3, NULL, f3_fn, NULL);
SEG_END("CRT:main#005@L215");
SEG_BEGIN("CRT:main#006@L216");
    pthread_create(&tf4, NULL, f4_fn, NULL);
SEG_END("CRT:main#006@L216");
SEG_BEGIN("CRT:main#007@L217");
    pthread_create(&tf5, NULL, f5_fn, NULL);
SEG_END("CRT:main#007@L217");
SEG_BEGIN("CRT:main#008@L218");
    pthread_create(&tf6, NULL, f6_fn, NULL);
SEG_END("CRT:main#008@L218");
SEG_BEGIN("CRT:main#009@L219");
    pthread_create(&tf7, NULL, f7_fn, NULL);
SEG_END("CRT:main#009@L219");
SEG_BEGIN("CRT:main#010@L220");
    pthread_create(&tf8, NULL, f8_fn, NULL);
SEG_END("CRT:main#010@L220");
SEG_BEGIN("CRT:main#011@L221");
    pthread_create(&tf9, NULL, f9_fn, NULL);
SEG_END("CRT:main#011@L221");
SEG_BEGIN("CRT:main#012@L222");
    pthread_create(&tf10, NULL, f10_fn, NULL);
SEG_END("CRT:main#012@L222");
SEG_BEGIN("CRT:main#013@L223");
    pthread_create(&tf11, NULL, f11_fn, NULL);
SEG_END("CRT:main#013@L223");
SEG_BEGIN("CRT:main#014@L224");
    pthread_create(&tc0, NULL, c0_fn, NULL);
SEG_END("CRT:main#014@L224");
SEG_BEGIN("JON:main#015@L225");
    pthread_join(tc0, NULL);
SEG_END("JON:main#015@L225");
SEG_BEGIN("JON:main#016@L226");
    pthread_join(tc1, NULL);
SEG_END("JON:main#016@L226");
SEG_BEGIN("JON:main#017@L227");
    pthread_join(tc2, NULL);
SEG_END("JON:main#017@L227");
SEG_BEGIN("JON:main#018@L228");
    pthread_join(tc3, NULL);
SEG_END("JON:main#018@L228");
SEG_BEGIN("JON:main#019@L229");
    pthread_join(tc4, NULL);
SEG_END("JON:main#019@L229");
SEG_BEGIN("JON:main#020@L230");
    pthread_join(tf0, NULL);
SEG_END("JON:main#020@L230");
SEG_BEGIN("JON:main#021@L231");
    pthread_join(tf1, NULL);
SEG_END("JON:main#021@L231");
SEG_BEGIN("JON:main#022@L232");
    pthread_join(tf2, NULL);
SEG_END("JON:main#022@L232");
SEG_BEGIN("JON:main#023@L233");
    pthread_join(tf3, NULL);
SEG_END("JON:main#023@L233");
SEG_BEGIN("JON:main#024@L234");
    pthread_join(tf4, NULL);
SEG_END("JON:main#024@L234");
SEG_BEGIN("JON:main#025@L235");
    pthread_join(tf5, NULL);
SEG_END("JON:main#025@L235");
SEG_BEGIN("JON:main#026@L236");
    pthread_join(tf6, NULL);
SEG_END("JON:main#026@L236");
SEG_BEGIN("JON:main#027@L237");
    pthread_join(tf7, NULL);
SEG_END("JON:main#027@L237");
SEG_BEGIN("JON:main#028@L238");
    pthread_join(tf8, NULL);
SEG_END("JON:main#028@L238");
SEG_BEGIN("JON:main#029@L239");
    pthread_join(tf9, NULL);
SEG_END("JON:main#029@L239");
SEG_BEGIN("JON:main#030@L240");
    pthread_join(tf10, NULL);
SEG_END("JON:main#030@L240");
SEG_BEGIN("JON:main#031@L241");
    pthread_join(tf11, NULL);
SEG_END("JON:main#031@L241");
SEG_BEGIN("THR:main#032@242-242");
    return 0;
SEG_END("THR:main#032@242-242");
}
