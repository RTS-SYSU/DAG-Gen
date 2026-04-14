#define _GNU_SOURCE
#include "prio_runtime.h"
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define C1 25.0
#define C2 45.0
#define C3 20.0
#define C4 10.0
#define C5 1400.0
#define C6 15.0
#define C7 1100.0
#define C8 15.0
#define C9 900.0
#define C10 60.0
#define C11 420.0
#define C12 60.0
#define C13 380.0
#define C14 60.0
#define C15 340.0

#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

#define MAT_N 64

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];
static volatile double g_busy_sink = 0.0;

static pthread_t thread_key_a;
static pthread_t thread_key_b;
static pthread_t thread_key_c;
static pthread_t thread_fill_x;
static pthread_t thread_fill_y;
static pthread_t thread_fill_z;

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

static void *worker_key_c(void *arg)
{
    l1_set_thread_prio_fifo(94);
    pthread_mutex_lock(&mutex_08);
    busy_wait_seconds(C9);
    pthread_mutex_unlock(&mutex_08);
l1_set_thread_prio_fifo(85);

    return NULL;
}

static void *worker_key_b(void *arg)
{
    l1_set_thread_prio_fifo(95);
    pthread_mutex_lock(&mutex_06);
    busy_wait_seconds(C7);
    pthread_mutex_unlock(&mutex_06);
    pthread_create(&thread_key_c, NULL, worker_key_c, NULL);
    l1_set_thread_prio_fifo(87);
    pthread_mutex_lock(&mutex_07);
    busy_wait_seconds(C8);
    pthread_mutex_unlock(&mutex_07);
l1_set_thread_prio_fifo(83);

    return NULL;
}

static void *worker_key_a(void *arg)
{
    l1_set_thread_prio_fifo(96);
    pthread_mutex_lock(&mutex_04);
    busy_wait_seconds(C5);
    pthread_mutex_unlock(&mutex_04);
    pthread_create(&thread_key_b, NULL, worker_key_b, NULL);
    l1_set_thread_prio_fifo(86);
    pthread_mutex_lock(&mutex_05);
    busy_wait_seconds(C6);
    pthread_mutex_unlock(&mutex_05);
l1_set_thread_prio_fifo(84);

    return NULL;
}

static void *worker_fill_x(void *arg)
{
    l1_set_thread_prio_fifo(93);
    pthread_mutex_lock(&mutex_09);
    busy_wait_seconds(C10);
    pthread_mutex_unlock(&mutex_09);
    l1_set_thread_prio_fifo(91);
    pthread_mutex_lock(&mutex_10);
    busy_wait_seconds(C11);
    pthread_mutex_unlock(&mutex_10);
l1_set_thread_prio_fifo(80);

    return NULL;
}

static void *worker_fill_y(void *arg)
{
    l1_set_thread_prio_fifo(92);
    pthread_mutex_lock(&mutex_11);
    busy_wait_seconds(C12);
    pthread_mutex_unlock(&mutex_11);
    l1_set_thread_prio_fifo(89);
    pthread_mutex_lock(&mutex_12);
    busy_wait_seconds(C13);
    pthread_mutex_unlock(&mutex_12);
l1_set_thread_prio_fifo(79);

    return NULL;
}

static void *worker_fill_z(void *arg)
{
    l1_set_thread_prio_fifo(90);
    pthread_mutex_lock(&mutex_13);
    busy_wait_seconds(C14);
    pthread_mutex_unlock(&mutex_13);
    l1_set_thread_prio_fifo(88);
    pthread_mutex_lock(&mutex_14);
    busy_wait_seconds(C15);
    pthread_mutex_unlock(&mutex_14);
l1_set_thread_prio_fifo(81);

    return NULL;
}

int main(void)
{
    struct timespec ts_main_begin, ts_main_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);
    l1_set_thread_prio_fifo(99);
    pthread_mutex_lock(&mutex_16);
    init_matrices();
    cpu_set_t cpu_set;
    CPU_ZERO(&cpu_set);
    CPU_SET(0, &cpu_set);
    CPU_SET(1, &cpu_set);
    if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0)
    {
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
    }
    pthread_mutex_unlock(&mutex_16);
    l1_set_thread_prio_fifo(98);
    pthread_mutex_lock(&mutex_01);
    busy_wait_seconds(C1);
    pthread_mutex_unlock(&mutex_01);
    pthread_create(&thread_fill_x, NULL, worker_fill_x, NULL);
    pthread_create(&thread_fill_y, NULL, worker_fill_y, NULL);
    pthread_create(&thread_fill_z, NULL, worker_fill_z, NULL);
    l1_set_thread_prio_fifo(97);
    pthread_mutex_lock(&mutex_02);
    busy_wait_seconds(C2);
    pthread_mutex_unlock(&mutex_02);
    pthread_create(&thread_key_a, NULL, worker_key_a, NULL);
    l1_set_thread_prio_fifo(82);
    pthread_join(thread_key_a, NULL);
    pthread_join(thread_key_b, NULL);
    pthread_join(thread_key_c, NULL);
    pthread_mutex_lock(&mutex_03);
    busy_wait_seconds(C3);
    pthread_mutex_unlock(&mutex_03);
    l1_set_thread_prio_fifo(78);
    pthread_join(thread_fill_x, NULL);
    pthread_join(thread_fill_y, NULL);
    pthread_join(thread_fill_z, NULL);
    pthread_mutex_lock(&mutex_15);
    busy_wait_seconds(C4);
    pthread_mutex_unlock(&mutex_15);
    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);
    {
        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)
            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;
        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\n", main_s);
    }
    return 0;
}
