#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define C1 40.0
#define C2 30.0
#define C3 20.0
#define C4 20.0
#define C5 900.0
#define C6 60.0
#define C7 700.0
#define C8 50.0
#define C9 850.0
#define C10 40.0
#define C11 500.0
#define C12 180.0
#define C13 520.0
#define C14 160.0
#define C15 480.0

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
    pthread_mutex_lock(&mutex_08);
    busy_wait_seconds(C9);
    pthread_mutex_unlock(&mutex_08);

    return NULL;
}

static void *worker_key_b(void *arg)
{
    pthread_mutex_lock(&mutex_06);
    busy_wait_seconds(C7);
    pthread_mutex_unlock(&mutex_06);
    pthread_create(&thread_key_c, NULL, worker_key_c, NULL);
    pthread_mutex_lock(&mutex_07);
    busy_wait_seconds(C8);
    pthread_mutex_unlock(&mutex_07);

    return NULL;
}

static void *worker_key_a(void *arg)
{
    pthread_mutex_lock(&mutex_04);
    busy_wait_seconds(C5);
    pthread_mutex_unlock(&mutex_04);
    pthread_create(&thread_key_b, NULL, worker_key_b, NULL);
    pthread_mutex_lock(&mutex_05);
    busy_wait_seconds(C6);
    pthread_mutex_unlock(&mutex_05);

    return NULL;
}

static void *worker_fill_x(void *arg)
{
    pthread_mutex_lock(&mutex_09);
    busy_wait_seconds(C10);
    pthread_mutex_unlock(&mutex_09);
    pthread_mutex_lock(&mutex_10);
    busy_wait_seconds(C11);
    pthread_mutex_unlock(&mutex_10);

    return NULL;
}

static void *worker_fill_y(void *arg)
{
    pthread_mutex_lock(&mutex_11);
    busy_wait_seconds(C12);
    pthread_mutex_unlock(&mutex_11);
    pthread_mutex_lock(&mutex_12);
    busy_wait_seconds(C13);
    pthread_mutex_unlock(&mutex_12);

    return NULL;
}

static void *worker_fill_z(void *arg)
{
    pthread_mutex_lock(&mutex_13);
    busy_wait_seconds(C14);
    pthread_mutex_unlock(&mutex_13);
    pthread_mutex_lock(&mutex_14);
    busy_wait_seconds(C15);
    pthread_mutex_unlock(&mutex_14);

    return NULL;
}

int main(void)
{
    struct timespec ts_main_begin, ts_main_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);
    pthread_mutex_lock(&mutex_16);
    init_matrices();
    cpu_set_t cpu_set;
    CPU_ZERO(&cpu_set);
    CPU_SET(6, &cpu_set);
    CPU_SET(7, &cpu_set);
    if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0)
    {
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
    }
    pthread_mutex_unlock(&mutex_16);
    pthread_mutex_lock(&mutex_01);
    busy_wait_seconds(C1);
    pthread_mutex_unlock(&mutex_01);
    pthread_create(&thread_fill_x, NULL, worker_fill_x, NULL);
    pthread_create(&thread_fill_y, NULL, worker_fill_y, NULL);
    pthread_create(&thread_fill_z, NULL, worker_fill_z, NULL);
    pthread_create(&thread_key_a, NULL, worker_key_a, NULL);
    pthread_mutex_lock(&mutex_02);
    busy_wait_seconds(C2);
    pthread_mutex_unlock(&mutex_02);
    pthread_join(thread_key_a, NULL);
    pthread_join(thread_key_b, NULL);
    pthread_join(thread_key_c, NULL);
    pthread_mutex_lock(&mutex_03);
    busy_wait_seconds(C3);
    pthread_mutex_unlock(&mutex_03);
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
