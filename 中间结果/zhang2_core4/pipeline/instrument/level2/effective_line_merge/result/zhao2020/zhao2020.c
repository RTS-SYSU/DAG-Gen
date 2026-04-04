#define _GNU_SOURCE
#include "prio_runtime.h"
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define C1 20.0
#define C2 12.0
#define C3 12.0
#define C4 12.0
#define C5 10.0
#define C6 10.0
#define C7 780.0
#define C8 220.0
#define C9 740.0
#define C10 210.0
#define C11 700.0
#define C12 200.0
#define C13 660.0
#define C14 190.0
#define C15 900.0
#define C16 15.0
#define C17 860.0
#define C18 15.0
#define C19 80.0
#define C20 8.0
#define C21 80.0
#define C22 8.0
#define C23 70.0
#define C24 8.0
#define C25 70.0
#define C26 8.0
#define C27 2000.0
#define C28 1900.0
#define C29 1800.0
#define C30 1700.0

#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

#define MAT_N 64

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];
static volatile double g_busy_sink = 0.0;

static pthread_t thread_blocker_a;
static pthread_t thread_blocker_b;
static pthread_t thread_blocker_c;
static pthread_t thread_blocker_d;
static pthread_t thread_launcher_l;
static pthread_t thread_launcher_r;
static pthread_t thread_gate_1;
static pthread_t thread_gate_2;
static pthread_t thread_gate_3;
static pthread_t thread_gate_4;
static pthread_t thread_tail_1;
static pthread_t thread_tail_2;
static pthread_t thread_tail_3;
static pthread_t thread_tail_4;

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
static pthread_mutex_t mutex_24 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_25 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_26 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_27 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_28 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_29 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_30 = PTHREAD_MUTEX_INITIALIZER;

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
    l1_set_thread_prio_fifo(96);
    pthread_mutex_lock(&mutex_27);
    busy_wait_seconds(C27);
    pthread_mutex_unlock(&mutex_27);

    return NULL;
}

static void *tail_worker_2(void *arg)
{
    l1_set_thread_prio_fifo(89);
    pthread_mutex_lock(&mutex_28);
    busy_wait_seconds(C28);
    pthread_mutex_unlock(&mutex_28);

    return NULL;
}

static void *tail_worker_3(void *arg)
{
    l1_set_thread_prio_fifo(91);
    pthread_mutex_lock(&mutex_29);
    busy_wait_seconds(C29);
    pthread_mutex_unlock(&mutex_29);

    return NULL;
}

static void *tail_worker_4(void *arg)
{
    l1_set_thread_prio_fifo(87);
    pthread_mutex_lock(&mutex_30);
    busy_wait_seconds(C30);
    pthread_mutex_unlock(&mutex_30);

    return NULL;
}

static void *gate_worker_1(void *arg)
{
    l1_set_thread_prio_fifo(97);
    pthread_mutex_lock(&mutex_19);
    busy_wait_seconds(C19);
    pthread_mutex_unlock(&mutex_19);
    pthread_create(&thread_tail_1, NULL, tail_worker_1, NULL);
    l1_set_thread_prio_fifo(80);
    pthread_mutex_lock(&mutex_20);
    busy_wait_seconds(C20);
    pthread_mutex_unlock(&mutex_20);

    return NULL;
}

static void *gate_worker_2(void *arg)
{
    l1_set_thread_prio_fifo(90);
    pthread_mutex_lock(&mutex_21);
    busy_wait_seconds(C21);
    pthread_mutex_unlock(&mutex_21);
    pthread_create(&thread_tail_2, NULL, tail_worker_2, NULL);
    l1_set_thread_prio_fifo(79);
    pthread_mutex_lock(&mutex_22);
    busy_wait_seconds(C22);
    pthread_mutex_unlock(&mutex_22);

    return NULL;
}

static void *gate_worker_3(void *arg)
{
    l1_set_thread_prio_fifo(92);
    pthread_mutex_lock(&mutex_23);
    busy_wait_seconds(C23);
    pthread_mutex_unlock(&mutex_23);
    pthread_create(&thread_tail_3, NULL, tail_worker_3, NULL);
    l1_set_thread_prio_fifo(78);
    pthread_mutex_lock(&mutex_24);
    busy_wait_seconds(C24);
    pthread_mutex_unlock(&mutex_24);

    return NULL;
}

static void *gate_worker_4(void *arg)
{
    l1_set_thread_prio_fifo(88);
    pthread_mutex_lock(&mutex_25);
    busy_wait_seconds(C25);
    pthread_mutex_unlock(&mutex_25);
    pthread_create(&thread_tail_4, NULL, tail_worker_4, NULL);
    l1_set_thread_prio_fifo(81);
    pthread_mutex_lock(&mutex_26);
    busy_wait_seconds(C26);
    pthread_mutex_unlock(&mutex_26);

    return NULL;
}

static void *launcher_l(void *arg)
{
    l1_set_thread_prio_fifo(98);
    pthread_mutex_lock(&mutex_15);
    busy_wait_seconds(C15);
    pthread_mutex_unlock(&mutex_15);
    pthread_create(&thread_gate_1, NULL, gate_worker_1, NULL);
    pthread_create(&thread_gate_2, NULL, gate_worker_2, NULL);
    l1_set_thread_prio_fifo(82);
    pthread_mutex_lock(&mutex_16);
    busy_wait_seconds(C16);
    pthread_mutex_unlock(&mutex_16);

    return NULL;
}

static void *launcher_r(void *arg)
{
    l1_set_thread_prio_fifo(93);
    pthread_mutex_lock(&mutex_17);
    busy_wait_seconds(C17);
    pthread_mutex_unlock(&mutex_17);
    pthread_create(&thread_gate_3, NULL, gate_worker_3, NULL);
    pthread_create(&thread_gate_4, NULL, gate_worker_4, NULL);
    l1_set_thread_prio_fifo(83);
    pthread_mutex_lock(&mutex_18);
    busy_wait_seconds(C18);
    pthread_mutex_unlock(&mutex_18);

    return NULL;
}

static void *blocker_a(void *arg)
{
    l1_set_thread_prio_fifo(73);
    pthread_mutex_lock(&mutex_07);
    busy_wait_seconds(C7);
    pthread_mutex_unlock(&mutex_07);
    l1_set_thread_prio_fifo(72);
    pthread_mutex_lock(&mutex_08);
    busy_wait_seconds(C8);
    pthread_mutex_unlock(&mutex_08);

    return NULL;
}

static void *blocker_b(void *arg)
{
    l1_set_thread_prio_fifo(77);
    pthread_mutex_lock(&mutex_09);
    busy_wait_seconds(C9);
    pthread_mutex_unlock(&mutex_09);
    l1_set_thread_prio_fifo(76);
    pthread_mutex_lock(&mutex_10);
    busy_wait_seconds(C10);
    pthread_mutex_unlock(&mutex_10);

    return NULL;
}

static void *blocker_c(void *arg)
{
    l1_set_thread_prio_fifo(71);
    pthread_mutex_lock(&mutex_11);
    busy_wait_seconds(C11);
    pthread_mutex_unlock(&mutex_11);
    l1_set_thread_prio_fifo(70);
    pthread_mutex_lock(&mutex_12);
    busy_wait_seconds(C12);
    pthread_mutex_unlock(&mutex_12);

    return NULL;
}

static void *blocker_d(void *arg)
{
    l1_set_thread_prio_fifo(75);
    pthread_mutex_lock(&mutex_13);
    busy_wait_seconds(C13);
    pthread_mutex_unlock(&mutex_13);
    l1_set_thread_prio_fifo(74);
    pthread_mutex_lock(&mutex_14);
    busy_wait_seconds(C14);
    pthread_mutex_unlock(&mutex_14);

    return NULL;
}

int main(void)
{
    l1_set_thread_prio_fifo(99);
    pthread_mutex_lock(&mutex_01);
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
    pthread_mutex_unlock(&mutex_01);

    pthread_create(&thread_blocker_a, NULL, blocker_a, NULL);
    pthread_create(&thread_blocker_b, NULL, blocker_b, NULL);
    pthread_create(&thread_blocker_c, NULL, blocker_c, NULL);
    pthread_create(&thread_blocker_d, NULL, blocker_d, NULL);
    pthread_create(&thread_launcher_l, NULL, launcher_l, NULL);
    pthread_create(&thread_launcher_r, NULL, launcher_r, NULL);

    l1_set_thread_prio_fifo(86);
    pthread_mutex_lock(&mutex_02);
    busy_wait_seconds(C2);
    pthread_mutex_unlock(&mutex_02);

    l1_set_thread_prio_fifo(85);
    pthread_join(thread_launcher_l, NULL);
    pthread_join(thread_launcher_r, NULL);

    pthread_mutex_lock(&mutex_03);
    busy_wait_seconds(C3);
    pthread_mutex_unlock(&mutex_03);

    l1_set_thread_prio_fifo(84);
    pthread_join(thread_gate_1, NULL);
    pthread_join(thread_gate_2, NULL);
    pthread_join(thread_gate_3, NULL);
    pthread_join(thread_gate_4, NULL);

    pthread_mutex_lock(&mutex_04);
    busy_wait_seconds(C4);
    pthread_mutex_unlock(&mutex_04);

    l1_set_thread_prio_fifo(95);
    pthread_join(thread_tail_1, NULL);
    pthread_join(thread_tail_2, NULL);
    pthread_join(thread_tail_3, NULL);
    pthread_join(thread_tail_4, NULL);

    pthread_mutex_lock(&mutex_05);
    busy_wait_seconds(C5);
    pthread_mutex_unlock(&mutex_05);

    l1_set_thread_prio_fifo(94);
    pthread_join(thread_blocker_a, NULL);
    pthread_join(thread_blocker_b, NULL);
    pthread_join(thread_blocker_c, NULL);
    pthread_join(thread_blocker_d, NULL);

    pthread_mutex_lock(&mutex_06);
    busy_wait_seconds(C6);
    pthread_mutex_unlock(&mutex_06);

    return 0;
}
