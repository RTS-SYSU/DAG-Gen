#define _GNU_SOURCE
#include "prio_runtime.h"
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * 权值设计（dag1 / 双核 cpu6,7）：制造「尾段 join + 单 straggler」关键路径。
 * - noise_b..f：极短 MU 双段 → 很快结束 join，停止与 tail/straggler 争核。
 * - noise_a：中等 C6 + 很长 C7 → main#005 前最后一批 join 的决定段（straggler）。
 * - tail C22/C23：加大且 C22>C23，与 straggler 并行阶段争 2 核，启发式会抬高 tail MU 优先级。
 * CFS/FIFO 在「多就绪线程抢 2 核」时更易错失该顺序；详见 实验文档/权值调整实验.md「dag1」。
 */
#define C1 15.0
#define C2 10.0
#define C3 12.0
#define C4 10.0
#define C5 8.0
#define C6 45.0
#define C7 1650.0
#define C8 28.0
#define C9 22.0
#define C10 28.0
#define C11 22.0
#define C12 28.0
#define C13 22.0
#define C14 28.0
#define C15 22.0
#define C16 28.0
#define C17 22.0
#define C18 55.0
#define C19 5.0
#define C20 55.0
#define C21 5.0
#define C22 2400.0
#define C23 1750.0

#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

#define MAT_N 64

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];
static volatile double g_busy_sink = 0.0;

static pthread_t thread_noise_a;
static pthread_t thread_noise_b;
static pthread_t thread_noise_c;
static pthread_t thread_noise_d;
static pthread_t thread_noise_e;
static pthread_t thread_noise_f;
static pthread_t thread_gate_1;
static pthread_t thread_gate_2;
static pthread_t thread_tail_1;
static pthread_t thread_tail_2;

static pthread_mutex_t mutex_01 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_02 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_03 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_04 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_05 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_06 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_07 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_08 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_09 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_10 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_11 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_12 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_13 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_14 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_15 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_16 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_17 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_18 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_19 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_20 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_21 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_22 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_23 = PTHREAD_MUTEX_INITIALIZER;

static void init_matrices(void)
{
    for (int i = 0; i < MAT_N; ++i)
    {
        for (int j = 0; j < MAT_N; ++j)
        {
            mat_a[i][j] = (double)(i + j + 1);
            mat_b[i][j] = (double)(i * 2 + j + 3);
            mat_c[i][j] = 0.0;
        }
    }
}

static void busy_wait_seconds(double seconds)
{
    int repeat_count = (int)(seconds * WORK_SCALE + 0.5);
    if (repeat_count < 1)
        repeat_count = 1;

    double x = 1.000001;
    double y = 0.999999;
    double z = 1.0000003;
    double acc = 0.0;

    for (int r = 0; r < repeat_count; ++r)
    {
        for (int i = 0; i < 512; ++i)
        {
            x = x * 1.0000001 + y * 0.9999999 + z * 0.0000001;
            y = y * 1.0000002 + z * 0.9999998 + x * 0.0000002;
            z = z * 1.0000003 + x * 0.9999997 + y * 0.0000003;
            acc += x * y + z;
        }
    }

    g_busy_sink += acc;
    mat_c[0][0] = g_busy_sink;
}

static void *tail_worker_1(void *arg)
{
    l1_set_thread_prio_fifo(97);
    pthread_mutex_lock(&mutex_22);
    busy_wait_seconds(C22);
    pthread_mutex_unlock(&mutex_22);

    return NULL;
}

static void *tail_worker_2(void *arg)
{
    l1_set_thread_prio_fifo(95);
    pthread_mutex_lock(&mutex_23);
    busy_wait_seconds(C23);
    pthread_mutex_unlock(&mutex_23);

    return NULL;
}

static void *gate_worker_1(void *arg)
{
    l1_set_thread_prio_fifo(98);
    pthread_mutex_lock(&mutex_18);
    busy_wait_seconds(C18);
    pthread_mutex_unlock(&mutex_18);
    pthread_create(&thread_tail_1, NULL, tail_worker_1, NULL);
    l1_set_thread_prio_fifo(81);
    pthread_mutex_lock(&mutex_19);
    busy_wait_seconds(C19);
    pthread_mutex_unlock(&mutex_19);

    return NULL;
}

static void *gate_worker_2(void *arg)
{
    l1_set_thread_prio_fifo(96);
    pthread_mutex_lock(&mutex_20);
    busy_wait_seconds(C20);
    pthread_mutex_unlock(&mutex_20);
    pthread_create(&thread_tail_2, NULL, tail_worker_2, NULL);
    l1_set_thread_prio_fifo(82);
    pthread_mutex_lock(&mutex_21);
    busy_wait_seconds(C21);
    pthread_mutex_unlock(&mutex_21);

    return NULL;
}

static void *noise_worker_a(void *arg)
{
    l1_set_thread_prio_fifo(94);
    pthread_mutex_lock(&mutex_06);
    busy_wait_seconds(C6);
    pthread_mutex_unlock(&mutex_06);
    l1_set_thread_prio_fifo(93);
    pthread_mutex_lock(&mutex_07);
    busy_wait_seconds(C7);
    pthread_mutex_unlock(&mutex_07);

    return NULL;
}

static void *noise_worker_b(void *arg)
{
    l1_set_thread_prio_fifo(92);
    pthread_mutex_lock(&mutex_08);
    busy_wait_seconds(C8);
    pthread_mutex_unlock(&mutex_08);
    l1_set_thread_prio_fifo(87);
    pthread_mutex_lock(&mutex_09);
    busy_wait_seconds(C9);
    pthread_mutex_unlock(&mutex_09);

    return NULL;
}

static void *noise_worker_c(void *arg)
{
    l1_set_thread_prio_fifo(88);
    pthread_mutex_lock(&mutex_10);
    busy_wait_seconds(C10);
    pthread_mutex_unlock(&mutex_10);
    l1_set_thread_prio_fifo(83);
    pthread_mutex_lock(&mutex_11);
    busy_wait_seconds(C11);
    pthread_mutex_unlock(&mutex_11);

    return NULL;
}

static void *noise_worker_d(void *arg)
{
    l1_set_thread_prio_fifo(90);
    pthread_mutex_lock(&mutex_12);
    busy_wait_seconds(C12);
    pthread_mutex_unlock(&mutex_12);
    l1_set_thread_prio_fifo(85);
    pthread_mutex_lock(&mutex_13);
    busy_wait_seconds(C13);
    pthread_mutex_unlock(&mutex_13);

    return NULL;
}

static void *noise_worker_e(void *arg)
{
    l1_set_thread_prio_fifo(91);
    pthread_mutex_lock(&mutex_14);
    busy_wait_seconds(C14);
    pthread_mutex_unlock(&mutex_14);
    l1_set_thread_prio_fifo(86);
    pthread_mutex_lock(&mutex_15);
    busy_wait_seconds(C15);
    pthread_mutex_unlock(&mutex_15);

    return NULL;
}

static void *noise_worker_f(void *arg)
{
    l1_set_thread_prio_fifo(89);
    pthread_mutex_lock(&mutex_16);
    busy_wait_seconds(C16);
    pthread_mutex_unlock(&mutex_16);
    l1_set_thread_prio_fifo(80);
    pthread_mutex_lock(&mutex_17);
    busy_wait_seconds(C17);
    pthread_mutex_unlock(&mutex_17);

    return NULL;
}

int main(void)
{
    struct timespec ts_main_begin, ts_main_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);
    l1_set_thread_prio_fifo(99);
    pthread_mutex_lock(&mutex_01);
    init_matrices();
    cpu_set_t cpu_set;
    CPU_ZERO(&cpu_set);
    CPU_SET(0, &cpu_set);
    CPU_SET(1, &cpu_set);
    if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0)
    {
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
    }
    busy_wait_seconds(C1);
    pthread_mutex_unlock(&mutex_01);

    pthread_create(&thread_noise_a, NULL, noise_worker_a, NULL);
    pthread_create(&thread_noise_b, NULL, noise_worker_b, NULL);
    pthread_create(&thread_noise_c, NULL, noise_worker_c, NULL);
    pthread_create(&thread_noise_d, NULL, noise_worker_d, NULL);
    pthread_create(&thread_noise_e, NULL, noise_worker_e, NULL);
    pthread_create(&thread_noise_f, NULL, noise_worker_f, NULL);
    pthread_create(&thread_gate_1, NULL, gate_worker_1, NULL);
    pthread_create(&thread_gate_2, NULL, gate_worker_2, NULL);

    l1_set_thread_prio_fifo(84);
    pthread_mutex_lock(&mutex_02);
    busy_wait_seconds(C2);
    pthread_mutex_unlock(&mutex_02);

    l1_set_thread_prio_fifo(79);
    pthread_join(thread_gate_1, NULL);
    pthread_join(thread_gate_2, NULL);

    pthread_mutex_lock(&mutex_03);
    busy_wait_seconds(C3);
    pthread_mutex_unlock(&mutex_03);

    l1_set_thread_prio_fifo(78);
    pthread_join(thread_tail_1, NULL);
    pthread_join(thread_tail_2, NULL);

    pthread_mutex_lock(&mutex_04);
    busy_wait_seconds(C4);
    pthread_mutex_unlock(&mutex_04);

    l1_set_thread_prio_fifo(77);
    pthread_join(thread_noise_a, NULL);
    pthread_join(thread_noise_b, NULL);
    pthread_join(thread_noise_c, NULL);
    pthread_join(thread_noise_d, NULL);
    pthread_join(thread_noise_e, NULL);
    pthread_join(thread_noise_f, NULL);

    pthread_mutex_lock(&mutex_05);
    busy_wait_seconds(C5);
    pthread_mutex_unlock(&mutex_05);

    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);
    {
        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)
            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;
        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\n", main_s);
    }
    return 0;
}
