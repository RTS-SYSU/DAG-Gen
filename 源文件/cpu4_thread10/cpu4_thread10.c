#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

/* 固定矩阵规模和重复次数，循环内不调用函数 */
#define MAT_N 64
#define REPEAT0 16
#define REPEAT1 18
#define REPEAT2 20
#define REPEAT3 22
#define REPEAT4 24
#define REPEAT5 26
#define REPEAT6 28
#define REPEAT7 30
#define REPEAT8 34
#define REPEAT9 38

/* 全局矩阵，避免在线程函数里分配 */
static double A[MAT_N][MAT_N];
static double B[MAT_N][MAT_N];
static double C[MAT_N][MAT_N];

/* 每个线程独立函数，循环内无函数调用，负载刻意拉开差异 */
static void *worker0(void *arg)
{
    int base = 0 * 5 + 1;
    for (int r = 0; r < REPEAT0; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker0 done\n");
    return NULL;
}

static void *worker1(void *arg)
{
    int base = 1 * 5 + 1;
    for (int r = 0; r < REPEAT1; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker1 done\n");
    return NULL;
}

static void *worker2(void *arg)
{
    int base = 2 * 5 + 1;
    for (int r = 0; r < REPEAT2; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker2 done\n");
}

static void *worker3(void *arg)
{
    int base = 3 * 5 + 1;
    for (int r = 0; r < REPEAT3; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker3 done\n");
    return NULL;
}

static void *worker4(void *arg)
{
    int base = 4 * 5 + 1;
    for (int r = 0; r < REPEAT4; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker4 done\n");
    return NULL;
}

static void *worker5(void *arg)
{
    int base = 5 * 5 + 1;
    for (int r = 0; r < REPEAT5; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker5 done\n");
    return NULL;
}

static void *worker6(void *arg)
{
    int base = 6 * 5 + 1;
    for (int r = 0; r < REPEAT6; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker6 done\n");
    return NULL;
}

static void *worker7(void *arg)
{
    int base = 7 * 5 + 1;
    for (int r = 0; r < REPEAT7; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker7 done\n");
    return NULL;
}

static void *worker8(void *arg)
{
    int base = 8 * 5 + 1;
    for (int r = 0; r < REPEAT8; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker8 done\n");
    return NULL;
}

static void *worker9(void *arg)
{
    int base = 9 * 5 + 1;
    for (int r = 0; r < REPEAT9; r++) {
        for (int i = 0; i < MAT_N; i++) {
            for (int j = 0; j < MAT_N; j++) {
                double acc = 0.0;
                for (int k = 0; k < MAT_N; k++) {
                    acc += (A[i][k] + base) * (B[k][j] + base);
                }
                C[i][j] = acc;
            }
        }
    }
    printf("worker9 done\n");
    return NULL;
}

int main(void)
{
    /* 预填充矩阵：循环里只有算术，没有函数调用 */
    for (int i = 0; i < MAT_N; i++) {
        for (int j = 0; j < MAT_N; j++) {
            A[i][j] = (double)(i + j + 1);
            B[i][j] = (double)(i * 2 + j + 3);
            C[i][j] = 0.0;
        }
    }

    /* 约束进程跑在前 4 个核心（可选） */
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    CPU_SET(1, &set);
    CPU_SET(2, &set);
    CPU_SET(3, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0) {
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
    }

    pthread_t t0, t1, t2, t3, t4, t5, t6, t7, t8, t9;
    int prio = 60;

    /* t0 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t0, &attr, worker0, NULL);
        pthread_attr_destroy(&attr);
    }

    /* t1 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t1, &attr, worker1, NULL);
        pthread_attr_destroy(&attr);
    }

    /* t2 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t2, &attr, worker2, NULL);
        pthread_attr_destroy(&attr);
    }

    /* t3 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t3, &attr, worker3, NULL);
        pthread_attr_destroy(&attr);
    }

    /* t4 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t4, &attr, worker4, NULL);
        pthread_attr_destroy(&attr);
    }

    /* t5 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t5, &attr, worker5, NULL);
        pthread_attr_destroy(&attr);
    }

    /* t6 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t6, &attr, worker6, NULL);
        pthread_attr_destroy(&attr);
    }

    /* t7 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t7, &attr, worker7, NULL);
        pthread_attr_destroy(&attr);
    }

    /* t8 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t8, &attr, worker8, NULL);
        pthread_attr_destroy(&attr);
    }

    /* t9 */
    {
        pthread_attr_t attr;
        struct sched_param sp;
        pthread_attr_init(&attr);
        pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
        pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
        memset(&sp, 0, sizeof(sp));
        sp.sched_priority = prio;
        pthread_attr_setschedparam(&attr, &sp);
        pthread_create(&t9, &attr, worker9, NULL);
        pthread_attr_destroy(&attr);
    }

    pthread_join(t0, NULL);
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    pthread_join(t3, NULL);
    pthread_join(t4, NULL);
    pthread_join(t5, NULL);
    pthread_join(t6, NULL);
    pthread_join(t7, NULL);
    pthread_join(t8, NULL);
    pthread_join(t9, NULL);

    printf("done. sample=%f\n", C[0][0]);
    return 0;
}
