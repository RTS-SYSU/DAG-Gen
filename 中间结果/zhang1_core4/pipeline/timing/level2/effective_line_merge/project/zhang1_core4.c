#define _GNU_SOURCE
#include "segtrace.h"
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define C1 20.0
#define C2 12.0
#define C3 15.0
#define C4 12.0
#define C5 10.0
#define C6 900.0
#define C7 220.0
#define C8 860.0
#define C9 210.0
#define C10 820.0
#define C11 200.0
#define C12 780.0
#define C13 190.0
#define C14 740.0
#define C15 180.0
#define C16 700.0
#define C17 170.0
#define C18 120.0
#define C19 10.0
#define C20 120.0
#define C21 10.0
#define C22 2000.0
#define C23 1800.0

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
    pthread_mutex_lock(&mutex_22);
SEG_BEGIN("MU:tail_worker_1#001@121-124");
    busy_wait_seconds(C22);
SEG_END("MU:tail_worker_1#001@121-124");
    pthread_mutex_unlock(&mutex_22);

    return NULL;
}

static void *tail_worker_2(void *arg)
{
    pthread_mutex_lock(&mutex_23);
SEG_BEGIN("MU:tail_worker_2#001@130-133");
    busy_wait_seconds(C23);
SEG_END("MU:tail_worker_2#001@130-133");
    pthread_mutex_unlock(&mutex_23);

    return NULL;
}

static void *gate_worker_1(void *arg)
{
    pthread_mutex_lock(&mutex_18);
SEG_BEGIN("MU:gate_worker_1#001@139-142");
    busy_wait_seconds(C18);
SEG_END("MU:gate_worker_1#001@139-142");
    pthread_mutex_unlock(&mutex_18);
    pthread_create(&thread_tail_1, NULL, tail_worker_1, NULL);
    pthread_mutex_lock(&mutex_19);
SEG_BEGIN("MU:gate_worker_1#002@143-146");
    busy_wait_seconds(C19);
SEG_END("MU:gate_worker_1#002@143-146");
    pthread_mutex_unlock(&mutex_19);

    return NULL;
}

static void *gate_worker_2(void *arg)
{
    pthread_mutex_lock(&mutex_20);
SEG_BEGIN("MU:gate_worker_2#001@152-155");
    busy_wait_seconds(C20);
SEG_END("MU:gate_worker_2#001@152-155");
    pthread_mutex_unlock(&mutex_20);
    pthread_create(&thread_tail_2, NULL, tail_worker_2, NULL);
    pthread_mutex_lock(&mutex_21);
SEG_BEGIN("MU:gate_worker_2#002@156-159");
    busy_wait_seconds(C21);
SEG_END("MU:gate_worker_2#002@156-159");
    pthread_mutex_unlock(&mutex_21);

    return NULL;
}

static void *noise_worker_a(void *arg)
{
    pthread_mutex_lock(&mutex_06);
SEG_BEGIN("MU:noise_worker_a#001@165-167");
    busy_wait_seconds(C6);
SEG_END("MU:noise_worker_a#001@165-167");
    pthread_mutex_unlock(&mutex_06);
    pthread_mutex_lock(&mutex_07);
SEG_BEGIN("MU:noise_worker_a#002@168-171");
    busy_wait_seconds(C7);
SEG_END("MU:noise_worker_a#002@168-171");
    pthread_mutex_unlock(&mutex_07);

    return NULL;
}

static void *noise_worker_b(void *arg)
{
    pthread_mutex_lock(&mutex_08);
SEG_BEGIN("MU:noise_worker_b#001@177-179");
    busy_wait_seconds(C8);
SEG_END("MU:noise_worker_b#001@177-179");
    pthread_mutex_unlock(&mutex_08);
    pthread_mutex_lock(&mutex_09);
SEG_BEGIN("MU:noise_worker_b#002@180-183");
    busy_wait_seconds(C9);
SEG_END("MU:noise_worker_b#002@180-183");
    pthread_mutex_unlock(&mutex_09);

    return NULL;
}

static void *noise_worker_c(void *arg)
{
    pthread_mutex_lock(&mutex_10);
SEG_BEGIN("MU:noise_worker_c#001@189-191");
    busy_wait_seconds(C10);
SEG_END("MU:noise_worker_c#001@189-191");
    pthread_mutex_unlock(&mutex_10);
    pthread_mutex_lock(&mutex_11);
SEG_BEGIN("MU:noise_worker_c#002@192-195");
    busy_wait_seconds(C11);
SEG_END("MU:noise_worker_c#002@192-195");
    pthread_mutex_unlock(&mutex_11);

    return NULL;
}

static void *noise_worker_d(void *arg)
{
    pthread_mutex_lock(&mutex_12);
SEG_BEGIN("MU:noise_worker_d#001@201-203");
    busy_wait_seconds(C12);
SEG_END("MU:noise_worker_d#001@201-203");
    pthread_mutex_unlock(&mutex_12);
    pthread_mutex_lock(&mutex_13);
SEG_BEGIN("MU:noise_worker_d#002@204-207");
    busy_wait_seconds(C13);
SEG_END("MU:noise_worker_d#002@204-207");
    pthread_mutex_unlock(&mutex_13);

    return NULL;
}

static void *noise_worker_e(void *arg)
{
    pthread_mutex_lock(&mutex_14);
SEG_BEGIN("MU:noise_worker_e#001@213-215");
    busy_wait_seconds(C14);
SEG_END("MU:noise_worker_e#001@213-215");
    pthread_mutex_unlock(&mutex_14);
    pthread_mutex_lock(&mutex_15);
SEG_BEGIN("MU:noise_worker_e#002@216-219");
    busy_wait_seconds(C15);
SEG_END("MU:noise_worker_e#002@216-219");
    pthread_mutex_unlock(&mutex_15);

    return NULL;
}

static void *noise_worker_f(void *arg)
{
    pthread_mutex_lock(&mutex_16);
SEG_BEGIN("MU:noise_worker_f#001@225-227");
    busy_wait_seconds(C16);
SEG_END("MU:noise_worker_f#001@225-227");
    pthread_mutex_unlock(&mutex_16);
    pthread_mutex_lock(&mutex_17);
SEG_BEGIN("MU:noise_worker_f#002@228-231");
    busy_wait_seconds(C17);
SEG_END("MU:noise_worker_f#002@228-231");
    pthread_mutex_unlock(&mutex_17);

    return NULL;
}

int main(void)
{
    pthread_mutex_lock(&mutex_01);
SEG_BEGIN("MU:main#001@237-260");
    init_matrices();
    cpu_set_t cpu_set;
    CPU_ZERO(&cpu_set);
    CPU_SET(4, &cpu_set);
    CPU_SET(5, &cpu_set);
    CPU_SET(6, &cpu_set);
    CPU_SET(7, &cpu_set);
    if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0)
    {
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
    }
    busy_wait_seconds(C1);
SEG_END("MU:main#001@237-260");
    pthread_mutex_unlock(&mutex_01);

    pthread_create(&thread_noise_a, NULL, noise_worker_a, NULL);
    pthread_create(&thread_noise_b, NULL, noise_worker_b, NULL);
    pthread_create(&thread_noise_c, NULL, noise_worker_c, NULL);
    pthread_create(&thread_noise_d, NULL, noise_worker_d, NULL);
    pthread_create(&thread_noise_e, NULL, noise_worker_e, NULL);
    pthread_create(&thread_noise_f, NULL, noise_worker_f, NULL);
    pthread_create(&thread_gate_1, NULL, gate_worker_1, NULL);
    pthread_create(&thread_gate_2, NULL, gate_worker_2, NULL);

    pthread_mutex_lock(&mutex_02);
SEG_BEGIN("MU:main#002@261-264");
    busy_wait_seconds(C2);
SEG_END("MU:main#002@261-264");
    pthread_mutex_unlock(&mutex_02);

    pthread_join(thread_gate_1, NULL);
    pthread_join(thread_gate_2, NULL);

    pthread_mutex_lock(&mutex_03);
SEG_BEGIN("MU:main#003@265-271");
    busy_wait_seconds(C3);
SEG_END("MU:main#003@265-271");
    pthread_mutex_unlock(&mutex_03);

    pthread_join(thread_tail_1, NULL);
    pthread_join(thread_tail_2, NULL);

    pthread_mutex_lock(&mutex_04);
SEG_BEGIN("MU:main#004@272-278");
    busy_wait_seconds(C4);
SEG_END("MU:main#004@272-278");
    pthread_mutex_unlock(&mutex_04);

    pthread_join(thread_noise_a, NULL);
    pthread_join(thread_noise_b, NULL);
    pthread_join(thread_noise_c, NULL);
    pthread_join(thread_noise_d, NULL);
    pthread_join(thread_noise_e, NULL);
    pthread_join(thread_noise_f, NULL);

    pthread_mutex_lock(&mutex_05);
SEG_BEGIN("MU:main#005@279-289");
    busy_wait_seconds(C5);
SEG_END("MU:main#005@279-289");
    pthread_mutex_unlock(&mutex_05);

    return 0;
}
