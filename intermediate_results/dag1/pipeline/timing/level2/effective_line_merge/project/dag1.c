#define _GNU_SOURCE
#include "segtrace.h"
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
SEG_BEGIN("MU:a_head#001@115-123");
    busy_wait_seconds(C3);
SEG_END("MU:a_head#001@115-123");
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
SEG_BEGIN("MU:b_left#001@129-133");
    busy_wait_seconds(C4);
SEG_END("MU:b_left#001@129-133");
    pthread_mutex_unlock(&mutex_04);
    sem_post(&sem_tail_left);
    return NULL;
}

static void *c_right(void *arg)
{
    sem_wait(&sem_right_start);
    pthread_mutex_lock(&mutex_05);
SEG_BEGIN("MU:c_right#001@139-143");
    busy_wait_seconds(C5);
SEG_END("MU:c_right#001@139-143");
    pthread_mutex_unlock(&mutex_05);
    sem_post(&sem_tail_right);
    return NULL;
}

static void *d_tail(void *arg)
{
    sem_wait(&sem_tail_left);
    sem_wait(&sem_tail_right);
    pthread_mutex_lock(&mutex_06);
SEG_BEGIN("MU:d_tail#001@149-153");
    busy_wait_seconds(C6);
SEG_END("MU:d_tail#001@149-153");
    pthread_mutex_unlock(&mutex_06);
    return NULL;
}

static void *filler_early_1(void *arg)
{
    pthread_mutex_lock(&mutex_07);
SEG_BEGIN("MU:filler_early_1#001@159-161");
    busy_wait_seconds(C7);
SEG_END("MU:filler_early_1#001@159-161");
    pthread_mutex_unlock(&mutex_07);
    return NULL;
}

static void *filler_early_2(void *arg)
{
    pthread_mutex_lock(&mutex_08);
SEG_BEGIN("MU:filler_early_2#001@167-169");
    busy_wait_seconds(C8);
SEG_END("MU:filler_early_2#001@167-169");
    pthread_mutex_unlock(&mutex_08);
    return NULL;
}

static void *filler_early_3(void *arg)
{
    pthread_mutex_lock(&mutex_09);
SEG_BEGIN("MU:filler_early_3#001@175-177");
    busy_wait_seconds(C9);
SEG_END("MU:filler_early_3#001@175-177");
    pthread_mutex_unlock(&mutex_09);
    return NULL;
}

static void *filler_early_4(void *arg)
{
    pthread_mutex_lock(&mutex_10);
SEG_BEGIN("MU:filler_early_4#001@183-185");
    busy_wait_seconds(C10);
SEG_END("MU:filler_early_4#001@183-185");
    pthread_mutex_unlock(&mutex_10);
    return NULL;
}

static void *filler_mid_1(void *arg)
{
    sem_wait(&sem_mid_1);
    pthread_mutex_lock(&mutex_11);
SEG_BEGIN("MU:filler_mid_1#001@191-194");
    busy_wait_seconds(C11);
SEG_END("MU:filler_mid_1#001@191-194");
    pthread_mutex_unlock(&mutex_11);
    return NULL;
}

static void *filler_mid_2(void *arg)
{
    sem_wait(&sem_mid_2);
    pthread_mutex_lock(&mutex_12);
SEG_BEGIN("MU:filler_mid_2#001@200-203");
    busy_wait_seconds(C12);
SEG_END("MU:filler_mid_2#001@200-203");
    pthread_mutex_unlock(&mutex_12);
    return NULL;
}

static void *filler_mid_3(void *arg)
{
    sem_wait(&sem_mid_3);
    pthread_mutex_lock(&mutex_13);
SEG_BEGIN("MU:filler_mid_3#001@209-212");
    busy_wait_seconds(C13);
SEG_END("MU:filler_mid_3#001@209-212");
    pthread_mutex_unlock(&mutex_13);
    return NULL;
}

static void *filler_mid_4(void *arg)
{
    sem_wait(&sem_mid_4);
    pthread_mutex_lock(&mutex_14);
SEG_BEGIN("MU:filler_mid_4#001@218-221");
    busy_wait_seconds(C14);
SEG_END("MU:filler_mid_4#001@218-221");
    pthread_mutex_unlock(&mutex_14);
    return NULL;
}

int main(void)
{
    pthread_mutex_lock(&mutex_01);
SEG_BEGIN("MU:main#001@227-246");
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
SEG_END("MU:main#001@227-246");
    pthread_mutex_unlock(&mutex_01);
SEG_BEGIN("SEG:main#002@247-247");

SEG_END("SEG:main#002@247-247");
    pthread_mutex_lock(&mutex_02);
SEG_BEGIN("MU:main#003@248-250");
    busy_wait_seconds(C2);
SEG_END("MU:main#003@248-250");
    pthread_mutex_unlock(&mutex_02);
SEG_BEGIN("SEG:main#004@251-263");

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
SEG_END("SEG:main#004@251-263");
SEG_BEGIN("SEG:main#005@264-264");

SEG_END("SEG:main#005@264-264");
    pthread_mutex_lock(&mutex_16);
SEG_BEGIN("MU:main#006@265-267");
    busy_wait_seconds(C16);
SEG_END("MU:main#006@265-267");
    pthread_mutex_unlock(&mutex_16);
SEG_BEGIN("SEG:main#007@268-268");

SEG_END("SEG:main#007@268-268");
SEG_BEGIN("SEG:main#008@269-281");
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

SEG_END("SEG:main#008@269-281");
    pthread_mutex_lock(&mutex_15);
SEG_BEGIN("MU:main#009@282-284");
    busy_wait_seconds(C15);
SEG_END("MU:main#009@282-284");
    pthread_mutex_unlock(&mutex_15);
    return 0;
}
