#define _GNU_SOURCE
#include <time.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>

#define C1 18.0
#define C2 12.0
#define C3 760.0
#define C4 920.0
#define C5 900.0
#define C6 980.0
#define C7 280.0
#define C8 280.0
#define C9 280.0
#define C10 280.0
#define C11 640.0
#define C12 620.0
#define C13 600.0
#define C14 580.0
#define C15 10.0
#define C16 10.0

#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

#define MAT_N 64

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];
static volatile double g_busy_sink = 0.0;

static pthread_t thread_a_head;
static pthread_t thread_b_left;
static pthread_t thread_c_right;
static pthread_t thread_d_tail;
static pthread_t thread_fill_early_1;
static pthread_t thread_fill_early_2;
static pthread_t thread_fill_early_3;
static pthread_t thread_fill_early_4;
static pthread_t thread_fill_mid_1;
static pthread_t thread_fill_mid_2;
static pthread_t thread_fill_mid_3;
static pthread_t thread_fill_mid_4;

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

static sem_t sem_left_start;
static sem_t sem_right_start;
static sem_t sem_tail_left;
static sem_t sem_tail_right;
static sem_t sem_mid_1;
static sem_t sem_mid_2;
static sem_t sem_mid_3;
static sem_t sem_mid_4;

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

static void *a_head(void *arg)
{
    pthread_mutex_lock(&mutex_03);
    busy_wait_seconds(C3);
    pthread_mutex_unlock(&mutex_03);
    sem_post(&sem_left_start);
    sem_post(&sem_right_start);
    sem_post(&sem_mid_1);
    sem_post(&sem_mid_2);
    sem_post(&sem_mid_3);
    sem_post(&sem_mid_4);
    return NULL;
}

static void *b_left(void *arg)
{
    sem_wait(&sem_left_start);
    pthread_mutex_lock(&mutex_04);
    busy_wait_seconds(C4);
    pthread_mutex_unlock(&mutex_04);
    sem_post(&sem_tail_left);
    return NULL;
}

static void *c_right(void *arg)
{
    sem_wait(&sem_right_start);
    pthread_mutex_lock(&mutex_05);
    busy_wait_seconds(C5);
    pthread_mutex_unlock(&mutex_05);
    sem_post(&sem_tail_right);
    return NULL;
}

static void *d_tail(void *arg)
{
    sem_wait(&sem_tail_left);
    sem_wait(&sem_tail_right);
    pthread_mutex_lock(&mutex_06);
    busy_wait_seconds(C6);
    pthread_mutex_unlock(&mutex_06);
    return NULL;
}

static void *filler_early_1(void *arg)
{
    pthread_mutex_lock(&mutex_07);
    busy_wait_seconds(C7);
    pthread_mutex_unlock(&mutex_07);
    return NULL;
}

static void *filler_early_2(void *arg)
{
    pthread_mutex_lock(&mutex_08);
    busy_wait_seconds(C8);
    pthread_mutex_unlock(&mutex_08);
    return NULL;
}

static void *filler_early_3(void *arg)
{
    pthread_mutex_lock(&mutex_09);
    busy_wait_seconds(C9);
    pthread_mutex_unlock(&mutex_09);
    return NULL;
}

static void *filler_early_4(void *arg)
{
    pthread_mutex_lock(&mutex_10);
    busy_wait_seconds(C10);
    pthread_mutex_unlock(&mutex_10);
    return NULL;
}

static void *filler_mid_1(void *arg)
{
    sem_wait(&sem_mid_1);
    pthread_mutex_lock(&mutex_11);
    busy_wait_seconds(C11);
    pthread_mutex_unlock(&mutex_11);
    return NULL;
}

static void *filler_mid_2(void *arg)
{
    sem_wait(&sem_mid_2);
    pthread_mutex_lock(&mutex_12);
    busy_wait_seconds(C12);
    pthread_mutex_unlock(&mutex_12);
    return NULL;
}

static void *filler_mid_3(void *arg)
{
    sem_wait(&sem_mid_3);
    pthread_mutex_lock(&mutex_13);
    busy_wait_seconds(C13);
    pthread_mutex_unlock(&mutex_13);
    return NULL;
}

static void *filler_mid_4(void *arg)
{
    sem_wait(&sem_mid_4);
    pthread_mutex_lock(&mutex_14);
    busy_wait_seconds(C14);
    pthread_mutex_unlock(&mutex_14);
    return NULL;
}

int main(void)
{
    struct timespec ts_main_begin, ts_main_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);
    pthread_mutex_lock(&mutex_01);
    init_matrices();
    if (sem_init(&sem_left_start, 0, 0) != 0)
        return 1;
    if (sem_init(&sem_right_start, 0, 0) != 0)
        return 1;
    if (sem_init(&sem_tail_left, 0, 0) != 0)
        return 1;
    if (sem_init(&sem_tail_right, 0, 0) != 0)
        return 1;
    if (sem_init(&sem_mid_1, 0, 0) != 0)
        return 1;
    if (sem_init(&sem_mid_2, 0, 0) != 0)
        return 1;
    if (sem_init(&sem_mid_3, 0, 0) != 0)
        return 1;
    if (sem_init(&sem_mid_4, 0, 0) != 0)
        return 1;
    busy_wait_seconds(C1);
    pthread_mutex_unlock(&mutex_01);

    pthread_mutex_lock(&mutex_02);
    busy_wait_seconds(C2);
    pthread_mutex_unlock(&mutex_02);

    pthread_create(&thread_fill_early_1, NULL, filler_early_1, NULL);
    pthread_create(&thread_fill_early_2, NULL, filler_early_2, NULL);
    pthread_create(&thread_fill_early_3, NULL, filler_early_3, NULL);
    pthread_create(&thread_fill_early_4, NULL, filler_early_4, NULL);
    pthread_create(&thread_fill_mid_1, NULL, filler_mid_1, NULL);
    pthread_create(&thread_fill_mid_2, NULL, filler_mid_2, NULL);
    pthread_create(&thread_fill_mid_3, NULL, filler_mid_3, NULL);
    pthread_create(&thread_fill_mid_4, NULL, filler_mid_4, NULL);
    pthread_create(&thread_d_tail, NULL, d_tail, NULL);
    pthread_create(&thread_c_right, NULL, c_right, NULL);
    pthread_create(&thread_b_left, NULL, b_left, NULL);
    pthread_create(&thread_a_head, NULL, a_head, NULL);

    pthread_mutex_lock(&mutex_16);
    busy_wait_seconds(C16);
    pthread_mutex_unlock(&mutex_16);

    pthread_join(thread_fill_early_1, NULL);
    pthread_join(thread_fill_early_2, NULL);
    pthread_join(thread_fill_early_3, NULL);
    pthread_join(thread_fill_early_4, NULL);
    pthread_join(thread_fill_mid_1, NULL);
    pthread_join(thread_fill_mid_2, NULL);
    pthread_join(thread_fill_mid_3, NULL);
    pthread_join(thread_fill_mid_4, NULL);
    pthread_join(thread_d_tail, NULL);
    pthread_join(thread_c_right, NULL);
    pthread_join(thread_b_left, NULL);
    pthread_join(thread_a_head, NULL);

    pthread_mutex_lock(&mutex_15);
    busy_wait_seconds(C15);
    pthread_mutex_unlock(&mutex_15);
    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);
    {
        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)
            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;
        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\n", main_s);
    }
    return 0;
}
