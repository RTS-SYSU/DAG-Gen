#define _GNU_SOURCE
#include "prio_runtime.h"
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
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
#define C1 100.0
#define C2 5.0
#define C3 80.0
#define C4 6.0
#define C5 2.0
#define C6 220.0
#define C7 3.0
#define C8 4.0
#define C9 2.0
#define C10 2.0
#define C11 3.0
#define C12 6.0
#define C13 100.0
#define C14 5.0
#define C15 80.0
#define C16 100.0
#define F_LONG 28.0
#define F_SHORT 20.0

static void *c0_fn(void *arg);
static void *c1_fn(void *arg);
static void *c2_fn(void *arg);
static void *c3_fn(void *arg);



#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

static double A[MAT_N][MAT_N];
static double B[MAT_N][MAT_N];
static double C[MAT_N][MAT_N];
static volatile double g_busy_sink = 0.0;

static pthread_t tc0, tc1, tc2, tc3, tc4;

static sem_t sem1;
static sem_t sem2;
static sem_t sem3;
static sem_t sem4;
static sem_t sem5;
static sem_t sem6;

static pthread_mutex_t mutex1 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex2 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex3 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex4 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex5 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex6 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex7 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex8 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex9 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex10 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex11 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex12 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex13 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex14 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex15 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex16 = PTHREAD_MUTEX_INITIALIZER;

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
    int units = (int)(seconds * WORK_SCALE + 0.5);
    if (units < 1)
        units = 1;

    double x = 1.000001;
    double y = 0.999999;
    double z = 1.0000003;
    double acc = 0.0;

    for (int r = 0; r < units; ++r) {
        for (int i = 0; i < 512; ++i) {
            x = x * 1.0000001 + y * 0.9999999 + z * 0.0000001;
            y = y * 1.0000002 + z * 0.9999998 + x * 0.0000002;
            z = z * 1.0000003 + x * 0.9999997 + y * 0.0000003;
            acc += x * y + z;
        }
    }

    g_busy_sink += acc;
    C[0][0] = g_busy_sink;
}

static struct timespec g_prog_start;




static void *c2_fn(void *arg)
{

    l1_set_thread_prio_fifo(98);
    pthread_mutex_lock(&mutex1);
    busy_wait_seconds(C1);
    pthread_mutex_unlock(&mutex1);
    l1_set_thread_prio_fifo(90);
    sem_wait(&sem5);
    pthread_mutex_lock(&mutex2);
    busy_wait_seconds(C2);
    pthread_mutex_unlock(&mutex2);
    l1_set_thread_prio_fifo(94);
    sem_wait(&sem6);
    pthread_mutex_lock(&mutex3);
    busy_wait_seconds(C3);
    pthread_mutex_unlock(&mutex3);
    return NULL;
}

static void *c1_fn(void *arg)
{
    l1_set_thread_prio_fifo(92);
    pthread_mutex_lock(&mutex4);
    busy_wait_seconds(C4);
    pthread_mutex_unlock(&mutex4);
    pthread_create(&tc2, NULL, c2_fn, NULL);
        l1_set_thread_prio_fifo(85);
        sem_wait(&sem3);
    pthread_mutex_lock(&mutex5);
    busy_wait_seconds(C5);
    pthread_mutex_unlock(&mutex5);
    sem_post(&sem5);
    l1_set_thread_prio_fifo(99);
    sem_wait(&sem4);
    pthread_mutex_lock(&mutex6);
    busy_wait_seconds(C6);
    pthread_mutex_unlock(&mutex6);
    sem_post(&sem6);
    return NULL;
}

static void *c0_fn(void *arg)
{

    l1_set_thread_prio_fifo(87);
    pthread_mutex_lock(&mutex7);
    busy_wait_seconds(C7);
    pthread_mutex_unlock(&mutex7);
    pthread_create(&tc1, NULL, c1_fn, NULL);
    l1_set_thread_prio_fifo(89);
    sem_wait(&sem1);
    pthread_mutex_lock(&mutex8);
    busy_wait_seconds(C8);
    pthread_mutex_unlock(&mutex8);
    sem_post(&sem3);
    l1_set_thread_prio_fifo(84);
    sem_wait(&sem2);
    pthread_mutex_lock(&mutex9);
    busy_wait_seconds(C9);
    pthread_mutex_unlock(&mutex9);
    sem_post(&sem4);
    return NULL;
}


int main(void)
{
    struct timespec ts_main_begin, ts_main_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);
    l1_set_thread_prio_fifo(86);
    pthread_mutex_lock(&mutex10);
    struct timespec ts_prog_start, ts_prog_end;
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    CPU_SET(1, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0) {
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
    }

    init_matrices();
    clock_gettime(CLOCK_MONOTONIC, &g_prog_start);
    clock_gettime(CLOCK_MONOTONIC, &ts_prog_start);

    if (sem_init(&sem1, 0, 0) != 0) return 1;
    if (sem_init(&sem2, 0, 0) != 0) return 1;
    if (sem_init(&sem3, 0, 0) != 0) return 1;
    if (sem_init(&sem4, 0, 0) != 0) return 1;
    if (sem_init(&sem5, 0, 0) != 0) return 1;
    if (sem_init(&sem6, 0, 0) != 0) return 1;

    /* 启动关键链入口 + 填充任务 */
    /* 先创建填充任务，再创建关键链入口，便于 FIFO 先跑填充 */

    busy_wait_seconds(C10);
    pthread_mutex_unlock(&mutex10);
    pthread_create(&tc0, NULL, c0_fn, NULL);
    l1_set_thread_prio_fifo(88);
    pthread_mutex_lock(&mutex11);
    busy_wait_seconds(C11);
    pthread_mutex_unlock(&mutex11);
    sem_post(&sem1);
    l1_set_thread_prio_fifo(93);
    pthread_mutex_lock(&mutex12);
    busy_wait_seconds(C12);
    pthread_mutex_unlock(&mutex12);
    sem_post(&sem2);
    l1_set_thread_prio_fifo(96);
    pthread_mutex_lock(&mutex13);
    busy_wait_seconds(C13);
    pthread_mutex_unlock(&mutex13);
    l1_set_thread_prio_fifo(91);
    pthread_join(tc0, NULL);
    pthread_mutex_lock(&mutex14);
    busy_wait_seconds(C14);
    pthread_mutex_unlock(&mutex14);
    l1_set_thread_prio_fifo(95);
    pthread_join(tc1, NULL);
    pthread_mutex_lock(&mutex15);
    busy_wait_seconds(C15);
    pthread_mutex_unlock(&mutex15);
    l1_set_thread_prio_fifo(97);
    pthread_join(tc2, NULL);
    pthread_mutex_lock(&mutex16);
    busy_wait_seconds(C16);
    sem_destroy(&sem1);
    sem_destroy(&sem2);
    sem_destroy(&sem3);
    sem_destroy(&sem4);
    sem_destroy(&sem5);
    sem_destroy(&sem6);
        pthread_mutex_unlock(&mutex16);
    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);
    {
        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)
            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;
        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\n", main_s);
    }
    return 0;
}
