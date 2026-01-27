#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <time.h>

/* 设计强关键路径 + 海量短任务填充，凸显 LPF 收益：
 * 关键链：t0(15s) -> t1(13s) -> t2(11s) -> t3(9s) -> t4(7s)
 * 填充任务：t5..t9(各2s)，t10..t29(各1s)，t30..t49(各0.8s)，均无依赖，起始即 runnable
 * 所有耗时按 0.1x 缩放后执行。
 * 父线程只创建下一节点，不在内部 join；所有 join 在 main 统一回收，确保最大并行度。
 */

#define T0 30.0
#define T1 28.0
#define T2 26.0
#define T3 24.0
#define T4 22.0
#define T_FILL2 4.0   /* 0.4s 实际 */
#define T_FILL1 2.0   /* 0.2s 实际 */
#define T_FILL08 1.0  /* 0.1s 实际 */

#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 25000
#endif

static double A[MAT_N][MAT_N];
static double B[MAT_N][MAT_N];
static double C[MAT_N][MAT_N];

static pthread_t t0, t1, t2, t3, t4;
static pthread_t t5, t6, t7, t8, t9;
static pthread_t t10, t11, t12, t13, t14, t15, t16, t17, t18, t19;
static pthread_t t20, t21, t22, t23, t24, t25, t26, t27, t28, t29;
static pthread_t t30, t31, t32, t33, t34, t35, t36, t37, t38, t39;
static pthread_t t40, t41, t42, t43, t44, t45, t46, t47, t48, t49;

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

static double elapsed_seconds(const struct timespec *start, const struct timespec *end)
{
    long long ns = (end->tv_sec - start->tv_sec) * 1000000000LL +
                   (end->tv_nsec - start->tv_nsec);
    return (double)ns / 1e9;
}

static struct timespec g_prog_start;

static double since_prog_start(void)
{
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return elapsed_seconds(&g_prog_start, &now);
}

#define START_PRINT(name) printf("%s start (CPU %d) at %.3fs\n", name, sched_getcpu(), since_prog_start())
#define DONE_PRINT(name, target, ts_start, ts_end) \
    printf("%s done (CPU %d, target %.3fs, real %.3fs)\n", \
           name, sched_getcpu(), (target) * 0.1, elapsed_seconds(&(ts_start), &(ts_end)))

static void *thread4_fn(void *arg)
{
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread4");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T4);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread4", T4, ts_start, ts_end);
    return NULL;
}

static void *thread3_fn(void *arg)
{
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread3");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T3);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread3", T3, ts_start, ts_end);

    pthread_create(&t4, NULL, thread4_fn, NULL);
    return NULL;
}

static void *thread2_fn(void *arg)
{
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread2");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T2);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread2", T2, ts_start, ts_end);

    pthread_create(&t3, NULL, thread3_fn, NULL);
    return NULL;
}

static void *thread1_fn(void *arg)
{
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread1");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T1);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread1", T1, ts_start, ts_end);

    pthread_create(&t2, NULL, thread2_fn, NULL);
    return NULL;
}

static void *thread0_fn(void *arg)
{
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread0");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T0);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread0", T0, ts_start, ts_end);

    pthread_create(&t1, NULL, thread1_fn, NULL);
    return NULL;
}

static void run_fill_task(const char *name, double t)
{
    struct timespec ts_start, ts_end;
    START_PRINT(name);
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(t);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT(name, t, ts_start, ts_end);
}

#define DEFINE_FILL_FN(fn_name, dur, label)            \
    static void *fn_name(void *arg) {                  \
        (void)arg;                                    \
        run_fill_task(label, dur);                    \
        return NULL;                                  \
    }

DEFINE_FILL_FN(thread5_fn,  T_FILL2, "thread5")
DEFINE_FILL_FN(thread6_fn,  T_FILL2, "thread6")
DEFINE_FILL_FN(thread7_fn,  T_FILL2, "thread7")
DEFINE_FILL_FN(thread8_fn,  T_FILL2, "thread8")
DEFINE_FILL_FN(thread9_fn,  T_FILL2, "thread9")
DEFINE_FILL_FN(thread10_fn, T_FILL1, "thread10")
DEFINE_FILL_FN(thread11_fn, T_FILL1, "thread11")
DEFINE_FILL_FN(thread12_fn, T_FILL1, "thread12")
DEFINE_FILL_FN(thread13_fn, T_FILL1, "thread13")
DEFINE_FILL_FN(thread14_fn, T_FILL1, "thread14")
DEFINE_FILL_FN(thread15_fn, T_FILL1, "thread15")
DEFINE_FILL_FN(thread16_fn, T_FILL1, "thread16")
DEFINE_FILL_FN(thread17_fn, T_FILL1, "thread17")
DEFINE_FILL_FN(thread18_fn, T_FILL1, "thread18")
DEFINE_FILL_FN(thread19_fn, T_FILL1, "thread19")
DEFINE_FILL_FN(thread20_fn, T_FILL1, "thread20")
DEFINE_FILL_FN(thread21_fn, T_FILL1, "thread21")
DEFINE_FILL_FN(thread22_fn, T_FILL1, "thread22")
DEFINE_FILL_FN(thread23_fn, T_FILL1, "thread23")
DEFINE_FILL_FN(thread24_fn, T_FILL1, "thread24")
DEFINE_FILL_FN(thread25_fn, T_FILL1, "thread25")
DEFINE_FILL_FN(thread26_fn, T_FILL1, "thread26")
DEFINE_FILL_FN(thread27_fn, T_FILL1, "thread27")
DEFINE_FILL_FN(thread28_fn, T_FILL1, "thread28")
DEFINE_FILL_FN(thread29_fn, T_FILL1, "thread29")
DEFINE_FILL_FN(thread30_fn, T_FILL08, "thread30")
DEFINE_FILL_FN(thread31_fn, T_FILL08, "thread31")
DEFINE_FILL_FN(thread32_fn, T_FILL08, "thread32")
DEFINE_FILL_FN(thread33_fn, T_FILL08, "thread33")
DEFINE_FILL_FN(thread34_fn, T_FILL08, "thread34")
DEFINE_FILL_FN(thread35_fn, T_FILL08, "thread35")
DEFINE_FILL_FN(thread36_fn, T_FILL08, "thread36")
DEFINE_FILL_FN(thread37_fn, T_FILL08, "thread37")
DEFINE_FILL_FN(thread38_fn, T_FILL08, "thread38")
DEFINE_FILL_FN(thread39_fn, T_FILL08, "thread39")
DEFINE_FILL_FN(thread40_fn, T_FILL08, "thread40")
DEFINE_FILL_FN(thread41_fn, T_FILL08, "thread41")
DEFINE_FILL_FN(thread42_fn, T_FILL08, "thread42")
DEFINE_FILL_FN(thread43_fn, T_FILL08, "thread43")
DEFINE_FILL_FN(thread44_fn, T_FILL08, "thread44")
DEFINE_FILL_FN(thread45_fn, T_FILL08, "thread45")
DEFINE_FILL_FN(thread46_fn, T_FILL08, "thread46")
DEFINE_FILL_FN(thread47_fn, T_FILL08, "thread47")
DEFINE_FILL_FN(thread48_fn, T_FILL08, "thread48")
DEFINE_FILL_FN(thread49_fn, T_FILL08, "thread49")

int main(void)
{
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

    /* 大量短任务 + 关键链入口 */
    pthread_create(&t0, NULL, thread0_fn, NULL);
    pthread_create(&t5, NULL, thread5_fn, NULL);
    pthread_create(&t6, NULL, thread6_fn, NULL);
    pthread_create(&t7, NULL, thread7_fn, NULL);
    pthread_create(&t8, NULL, thread8_fn, NULL);
    pthread_create(&t9, NULL, thread9_fn, NULL);
    pthread_create(&t10, NULL, thread10_fn, NULL);
    pthread_create(&t11, NULL, thread11_fn, NULL);
    pthread_create(&t12, NULL, thread12_fn, NULL);
    pthread_create(&t13, NULL, thread13_fn, NULL);
    pthread_create(&t14, NULL, thread14_fn, NULL);
    pthread_create(&t15, NULL, thread15_fn, NULL);
    pthread_create(&t16, NULL, thread16_fn, NULL);
    pthread_create(&t17, NULL, thread17_fn, NULL);
    pthread_create(&t18, NULL, thread18_fn, NULL);
    pthread_create(&t19, NULL, thread19_fn, NULL);
    pthread_create(&t20, NULL, thread20_fn, NULL);
    pthread_create(&t21, NULL, thread21_fn, NULL);
    pthread_create(&t22, NULL, thread22_fn, NULL);
    pthread_create(&t23, NULL, thread23_fn, NULL);
    pthread_create(&t24, NULL, thread24_fn, NULL);
    pthread_create(&t25, NULL, thread25_fn, NULL);
    pthread_create(&t26, NULL, thread26_fn, NULL);
    pthread_create(&t27, NULL, thread27_fn, NULL);
    pthread_create(&t28, NULL, thread28_fn, NULL);
    pthread_create(&t29, NULL, thread29_fn, NULL);
    pthread_create(&t30, NULL, thread30_fn, NULL);
    pthread_create(&t31, NULL, thread31_fn, NULL);
    pthread_create(&t32, NULL, thread32_fn, NULL);
    pthread_create(&t33, NULL, thread33_fn, NULL);
    pthread_create(&t34, NULL, thread34_fn, NULL);
    pthread_create(&t35, NULL, thread35_fn, NULL);
    pthread_create(&t36, NULL, thread36_fn, NULL);
    pthread_create(&t37, NULL, thread37_fn, NULL);
    pthread_create(&t38, NULL, thread38_fn, NULL);
    pthread_create(&t39, NULL, thread39_fn, NULL);
    pthread_create(&t40, NULL, thread40_fn, NULL);
    pthread_create(&t41, NULL, thread41_fn, NULL);
    pthread_create(&t42, NULL, thread42_fn, NULL);
    pthread_create(&t43, NULL, thread43_fn, NULL);
    pthread_create(&t44, NULL, thread44_fn, NULL);
    pthread_create(&t45, NULL, thread45_fn, NULL);
    pthread_create(&t46, NULL, thread46_fn, NULL);
    pthread_create(&t47, NULL, thread47_fn, NULL);
    pthread_create(&t48, NULL, thread48_fn, NULL);
    pthread_create(&t49, NULL, thread49_fn, NULL);

    /* 统一回收 */
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
    pthread_join(t10, NULL);
    pthread_join(t11, NULL);
    pthread_join(t12, NULL);
    pthread_join(t13, NULL);
    pthread_join(t14, NULL);
    pthread_join(t15, NULL);
    pthread_join(t16, NULL);
    pthread_join(t17, NULL);
    pthread_join(t18, NULL);
    pthread_join(t19, NULL);
    pthread_join(t20, NULL);
    pthread_join(t21, NULL);
    pthread_join(t22, NULL);
    pthread_join(t23, NULL);
    pthread_join(t24, NULL);
    pthread_join(t25, NULL);
    pthread_join(t26, NULL);
    pthread_join(t27, NULL);
    pthread_join(t28, NULL);
    pthread_join(t29, NULL);
    pthread_join(t30, NULL);
    pthread_join(t31, NULL);
    pthread_join(t32, NULL);
    pthread_join(t33, NULL);
    pthread_join(t34, NULL);
    pthread_join(t35, NULL);
    pthread_join(t36, NULL);
    pthread_join(t37, NULL);
    pthread_join(t38, NULL);
    pthread_join(t39, NULL);
    pthread_join(t40, NULL);
    pthread_join(t41, NULL);
    pthread_join(t42, NULL);
    pthread_join(t43, NULL);
    pthread_join(t44, NULL);
    pthread_join(t45, NULL);
    pthread_join(t46, NULL);
    pthread_join(t47, NULL);
    pthread_join(t48, NULL);
    pthread_join(t49, NULL);

    clock_gettime(CLOCK_MONOTONIC, &ts_prog_end);
    printf("Program total time: %.3fs\n", elapsed_seconds(&ts_prog_start, &ts_prog_end));
    puts("all threads done");
    return 0;
}
