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
SEG_BEGIN("THR:c4_fn#001@86-98");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "c4", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(C4);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "c4", sched_getcpu(), C4 * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:c4_fn#001@86-98");
}

static void *c3_fn(void *arg)
{
SEG_BEGIN("THR:c3_fn#001@103-114");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "c3", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(C3);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "c3", sched_getcpu(), C3 * 0.1, (double)ns_real / 1e9);
SEG_END("THR:c3_fn#001@103-114");
SEG_BEGIN("CRT:c3_fn#002@L115");
    pthread_create(&tc4, NULL, c4_fn, NULL);
SEG_END("CRT:c3_fn#002@L115");
SEG_BEGIN("THR:c3_fn#003@116-116");
    return NULL;
SEG_END("THR:c3_fn#003@116-116");
}

static void *c2_fn(void *arg)
{
SEG_BEGIN("THR:c2_fn#001@121-132");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "c2", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(C2);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "c2", sched_getcpu(), C2 * 0.1, (double)ns_real / 1e9);
SEG_END("THR:c2_fn#001@121-132");
SEG_BEGIN("CRT:c2_fn#002@L133");
    pthread_create(&tc3, NULL, c3_fn, NULL);
SEG_END("CRT:c2_fn#002@L133");
SEG_BEGIN("THR:c2_fn#003@134-134");
    return NULL;
SEG_END("THR:c2_fn#003@134-134");
}

static void *c1_fn(void *arg)
{
SEG_BEGIN("THR:c1_fn#001@139-150");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "c1", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(C1);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "c1", sched_getcpu(), C1 * 0.1, (double)ns_real / 1e9);
SEG_END("THR:c1_fn#001@139-150");
SEG_BEGIN("CRT:c1_fn#002@L151");
    pthread_create(&tc2, NULL, c2_fn, NULL);
SEG_END("CRT:c1_fn#002@L151");
SEG_BEGIN("THR:c1_fn#003@152-152");
    return NULL;
SEG_END("THR:c1_fn#003@152-152");
}

static void *c0_fn(void *arg)
{
SEG_BEGIN("THR:c0_fn#001@157-168");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "c0", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(C0);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "c0", sched_getcpu(), C0 * 0.1, (double)ns_real / 1e9);
SEG_END("THR:c0_fn#001@157-168");
SEG_BEGIN("CRT:c0_fn#002@L169");
    pthread_create(&tc1, NULL, c1_fn, NULL);
SEG_END("CRT:c0_fn#002@L169");
SEG_BEGIN("THR:c0_fn#003@170-170");
    return NULL;
SEG_END("THR:c0_fn#003@170-170");
}

static void *f0_fn(void *arg)
{
SEG_BEGIN("THR:f0_fn#001@175-187");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f0", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f0", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f0_fn#001@175-187");
}

static void *f1_fn(void *arg)
{
SEG_BEGIN("THR:f1_fn#001@192-204");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f1", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f1", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f1_fn#001@192-204");
}

static void *f2_fn(void *arg)
{
SEG_BEGIN("THR:f2_fn#001@209-221");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f2", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f2", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f2_fn#001@209-221");
}

static void *f3_fn(void *arg)
{
SEG_BEGIN("THR:f3_fn#001@226-238");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f3", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f3", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f3_fn#001@226-238");
}

static void *f4_fn(void *arg)
{
SEG_BEGIN("THR:f4_fn#001@243-255");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f4", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f4", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f4_fn#001@243-255");
}

static void *f5_fn(void *arg)
{
SEG_BEGIN("THR:f5_fn#001@260-272");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f5", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f5", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f5_fn#001@260-272");
}

static void *f6_fn(void *arg)
{
SEG_BEGIN("THR:f6_fn#001@277-289");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f6", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f6", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f6_fn#001@277-289");
}

static void *f7_fn(void *arg)
{
SEG_BEGIN("THR:f7_fn#001@294-306");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f7", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f7", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f7_fn#001@294-306");
}

static void *f8_fn(void *arg)
{
SEG_BEGIN("THR:f8_fn#001@311-323");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f8", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f8", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f8_fn#001@311-323");
}

static void *f9_fn(void *arg)
{
SEG_BEGIN("THR:f9_fn#001@328-340");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f9", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +  
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f9", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f9_fn#001@328-340");
}

static void *f10_fn(void *arg)
{
SEG_BEGIN("THR:f10_fn#001@345-357");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f10", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_LONG);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f10", sched_getcpu(), F_LONG * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f10_fn#001@345-357");
}

static void *f11_fn(void *arg)
{
SEG_BEGIN("THR:f11_fn#001@362-374");
    struct timespec ts_start, ts_end;
    (void)arg;
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    long long ns_start = (ts_start.tv_sec - g_prog_start.tv_sec) * 1000000000LL +
                         (ts_start.tv_nsec - g_prog_start.tv_nsec);
    printf("%s start (CPU %d) at %.3fs\n", "f11", sched_getcpu(), (double)ns_start / 1e9);
    busy_wait_seconds(F_SHORT);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    long long ns_real = (ts_end.tv_sec - ts_start.tv_sec) * 1000000000LL +
                        (ts_end.tv_nsec - ts_start.tv_nsec);
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n",
           "f11", sched_getcpu(), F_SHORT * 0.1, (double)ns_real / 1e9);
    return NULL;
SEG_END("THR:f11_fn#001@362-374");
}

int main(void)
{
SEG_BEGIN("THR:main#001@379-395");
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
SEG_END("THR:main#001@379-395");
SEG_BEGIN("CRT:main#002@L396");
    pthread_create(&tf0, NULL, f0_fn, NULL);
SEG_END("CRT:main#002@L396");
SEG_BEGIN("CRT:main#003@L397");
    pthread_create(&tf1, NULL, f1_fn, NULL);
SEG_END("CRT:main#003@L397");
SEG_BEGIN("CRT:main#004@L398");
    pthread_create(&tf2, NULL, f2_fn, NULL);
SEG_END("CRT:main#004@L398");
SEG_BEGIN("CRT:main#005@L399");
    pthread_create(&tf3, NULL, f3_fn, NULL);
SEG_END("CRT:main#005@L399");
SEG_BEGIN("CRT:main#006@L400");
    pthread_create(&tf4, NULL, f4_fn, NULL);
SEG_END("CRT:main#006@L400");
SEG_BEGIN("CRT:main#007@L401");
    pthread_create(&tf5, NULL, f5_fn, NULL);
SEG_END("CRT:main#007@L401");
SEG_BEGIN("CRT:main#008@L402");
    pthread_create(&tf6, NULL, f6_fn, NULL);
SEG_END("CRT:main#008@L402");
SEG_BEGIN("CRT:main#009@L403");
    pthread_create(&tf7, NULL, f7_fn, NULL);
SEG_END("CRT:main#009@L403");
SEG_BEGIN("CRT:main#010@L404");
    pthread_create(&tf8, NULL, f8_fn, NULL);
SEG_END("CRT:main#010@L404");
SEG_BEGIN("CRT:main#011@L405");
    pthread_create(&tf9, NULL, f9_fn, NULL);
SEG_END("CRT:main#011@L405");
SEG_BEGIN("CRT:main#012@L406");
    pthread_create(&tf10, NULL, f10_fn, NULL);
SEG_END("CRT:main#012@L406");
SEG_BEGIN("CRT:main#013@L407");
    pthread_create(&tf11, NULL, f11_fn, NULL);
SEG_END("CRT:main#013@L407");
SEG_BEGIN("CRT:main#014@L408");
    pthread_create(&tc0, NULL, c0_fn, NULL);
SEG_END("CRT:main#014@L408");
SEG_BEGIN("JON:main#015@L409");
    pthread_join(tc0, NULL);
SEG_END("JON:main#015@L409");
SEG_BEGIN("JON:main#016@L410");
    pthread_join(tc1, NULL);
SEG_END("JON:main#016@L410");
SEG_BEGIN("JON:main#017@L411");
    pthread_join(tc2, NULL);
SEG_END("JON:main#017@L411");
SEG_BEGIN("JON:main#018@L412");
    pthread_join(tc3, NULL);
SEG_END("JON:main#018@L412");
SEG_BEGIN("JON:main#019@L413");
    pthread_join(tc4, NULL);
SEG_END("JON:main#019@L413");
SEG_BEGIN("JON:main#020@L414");
    pthread_join(tf0, NULL);
SEG_END("JON:main#020@L414");
SEG_BEGIN("JON:main#021@L415");
    pthread_join(tf1, NULL);
SEG_END("JON:main#021@L415");
SEG_BEGIN("JON:main#022@L416");
    pthread_join(tf2, NULL);
SEG_END("JON:main#022@L416");
SEG_BEGIN("JON:main#023@L417");
    pthread_join(tf3, NULL);
SEG_END("JON:main#023@L417");
SEG_BEGIN("JON:main#024@L418");
    pthread_join(tf4, NULL);
SEG_END("JON:main#024@L418");
SEG_BEGIN("JON:main#025@L419");
    pthread_join(tf5, NULL);
SEG_END("JON:main#025@L419");
SEG_BEGIN("JON:main#026@L420");
    pthread_join(tf6, NULL);
SEG_END("JON:main#026@L420");
SEG_BEGIN("JON:main#027@L421");
    pthread_join(tf7, NULL);
SEG_END("JON:main#027@L421");
SEG_BEGIN("JON:main#028@L422");
    pthread_join(tf8, NULL);
SEG_END("JON:main#028@L422");
SEG_BEGIN("JON:main#029@L423");
    pthread_join(tf9, NULL);
SEG_END("JON:main#029@L423");
SEG_BEGIN("JON:main#030@L424");
    pthread_join(tf10, NULL);
SEG_END("JON:main#030@L424");
SEG_BEGIN("JON:main#031@L425");
    pthread_join(tf11, NULL);
SEG_END("JON:main#031@L425");
SEG_BEGIN("THR:main#032@426-432");

    clock_gettime(CLOCK_MONOTONIC, &ts_prog_end);
    long long prog_ns = (ts_prog_end.tv_sec - ts_prog_start.tv_sec) * 1000000000LL +
                        (ts_prog_end.tv_nsec - ts_prog_start.tv_nsec);
    printf("Program total time: %.3fs\n", (double)prog_ns / 1e9);
    puts("all threads done");
    return 0;
SEG_END("THR:main#032@426-432");
}
