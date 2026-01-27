#define _GNU_SOURCE
#include "segtrace.h"
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
SEG_BEGIN("THR:thread4_fn#001@93-100");
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread4");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T4);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread4", T4, ts_start, ts_end);
    return NULL;
SEG_END("THR:thread4_fn#001@93-100");
}

static void *thread3_fn(void *arg)
{
SEG_BEGIN("THR:thread3_fn#001@105-112");
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread3");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T3);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread3", T3, ts_start, ts_end);

SEG_END("THR:thread3_fn#001@105-112");
SEG_BEGIN("CRT:thread3_fn#002@L113");
    pthread_create(&t4, NULL, thread4_fn, NULL);
SEG_END("CRT:thread3_fn#002@L113");
SEG_BEGIN("THR:thread3_fn#003@114-114");
    return NULL;
SEG_END("THR:thread3_fn#003@114-114");
}

static void *thread2_fn(void *arg)
{
SEG_BEGIN("THR:thread2_fn#001@119-126");
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread2");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T2);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread2", T2, ts_start, ts_end);

SEG_END("THR:thread2_fn#001@119-126");
SEG_BEGIN("CRT:thread2_fn#002@L127");
    pthread_create(&t3, NULL, thread3_fn, NULL);
SEG_END("CRT:thread2_fn#002@L127");
SEG_BEGIN("THR:thread2_fn#003@128-128");
    return NULL;
SEG_END("THR:thread2_fn#003@128-128");
}

static void *thread1_fn(void *arg)
{
SEG_BEGIN("THR:thread1_fn#001@133-140");
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread1");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T1);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread1", T1, ts_start, ts_end);

SEG_END("THR:thread1_fn#001@133-140");
SEG_BEGIN("CRT:thread1_fn#002@L141");
    pthread_create(&t2, NULL, thread2_fn, NULL);
SEG_END("CRT:thread1_fn#002@L141");
SEG_BEGIN("THR:thread1_fn#003@142-142");
    return NULL;
SEG_END("THR:thread1_fn#003@142-142");
}

static void *thread0_fn(void *arg)
{
SEG_BEGIN("THR:thread0_fn#001@147-154");
    struct timespec ts_start, ts_end;
    (void)arg;
    START_PRINT("thread0");
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    busy_wait_seconds(T0);
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    DONE_PRINT("thread0", T0, ts_start, ts_end);

SEG_END("THR:thread0_fn#001@147-154");
SEG_BEGIN("CRT:thread0_fn#002@L155");
    pthread_create(&t1, NULL, thread1_fn, NULL);
SEG_END("CRT:thread0_fn#002@L155");
SEG_BEGIN("THR:thread0_fn#003@156-156");
    return NULL;
SEG_END("THR:thread0_fn#003@156-156");
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
SEG_BEGIN("THR:main#001@224-239");
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
SEG_END("THR:main#001@224-239");
SEG_BEGIN("CRT:main#002@L240");
    pthread_create(&t0, NULL, thread0_fn, NULL);
SEG_END("CRT:main#002@L240");
SEG_BEGIN("CRT:main#003@L241");
    pthread_create(&t5, NULL, thread5_fn, NULL);
SEG_END("CRT:main#003@L241");
SEG_BEGIN("CRT:main#004@L242");
    pthread_create(&t6, NULL, thread6_fn, NULL);
SEG_END("CRT:main#004@L242");
SEG_BEGIN("CRT:main#005@L243");
    pthread_create(&t7, NULL, thread7_fn, NULL);
SEG_END("CRT:main#005@L243");
SEG_BEGIN("CRT:main#006@L244");
    pthread_create(&t8, NULL, thread8_fn, NULL);
SEG_END("CRT:main#006@L244");
SEG_BEGIN("CRT:main#007@L245");
    pthread_create(&t9, NULL, thread9_fn, NULL);
SEG_END("CRT:main#007@L245");
SEG_BEGIN("CRT:main#008@L246");
    pthread_create(&t10, NULL, thread10_fn, NULL);
SEG_END("CRT:main#008@L246");
SEG_BEGIN("CRT:main#009@L247");
    pthread_create(&t11, NULL, thread11_fn, NULL);
SEG_END("CRT:main#009@L247");
SEG_BEGIN("CRT:main#010@L248");
    pthread_create(&t12, NULL, thread12_fn, NULL);
SEG_END("CRT:main#010@L248");
SEG_BEGIN("CRT:main#011@L249");
    pthread_create(&t13, NULL, thread13_fn, NULL);
SEG_END("CRT:main#011@L249");
SEG_BEGIN("CRT:main#012@L250");
    pthread_create(&t14, NULL, thread14_fn, NULL);
SEG_END("CRT:main#012@L250");
SEG_BEGIN("CRT:main#013@L251");
    pthread_create(&t15, NULL, thread15_fn, NULL);
SEG_END("CRT:main#013@L251");
SEG_BEGIN("CRT:main#014@L252");
    pthread_create(&t16, NULL, thread16_fn, NULL);
SEG_END("CRT:main#014@L252");
SEG_BEGIN("CRT:main#015@L253");
    pthread_create(&t17, NULL, thread17_fn, NULL);
SEG_END("CRT:main#015@L253");
SEG_BEGIN("CRT:main#016@L254");
    pthread_create(&t18, NULL, thread18_fn, NULL);
SEG_END("CRT:main#016@L254");
SEG_BEGIN("CRT:main#017@L255");
    pthread_create(&t19, NULL, thread19_fn, NULL);
SEG_END("CRT:main#017@L255");
SEG_BEGIN("CRT:main#018@L256");
    pthread_create(&t20, NULL, thread20_fn, NULL);
SEG_END("CRT:main#018@L256");
SEG_BEGIN("CRT:main#019@L257");
    pthread_create(&t21, NULL, thread21_fn, NULL);
SEG_END("CRT:main#019@L257");
SEG_BEGIN("CRT:main#020@L258");
    pthread_create(&t22, NULL, thread22_fn, NULL);
SEG_END("CRT:main#020@L258");
SEG_BEGIN("CRT:main#021@L259");
    pthread_create(&t23, NULL, thread23_fn, NULL);
SEG_END("CRT:main#021@L259");
SEG_BEGIN("CRT:main#022@L260");
    pthread_create(&t24, NULL, thread24_fn, NULL);
SEG_END("CRT:main#022@L260");
SEG_BEGIN("CRT:main#023@L261");
    pthread_create(&t25, NULL, thread25_fn, NULL);
SEG_END("CRT:main#023@L261");
SEG_BEGIN("CRT:main#024@L262");
    pthread_create(&t26, NULL, thread26_fn, NULL);
SEG_END("CRT:main#024@L262");
SEG_BEGIN("CRT:main#025@L263");
    pthread_create(&t27, NULL, thread27_fn, NULL);
SEG_END("CRT:main#025@L263");
SEG_BEGIN("CRT:main#026@L264");
    pthread_create(&t28, NULL, thread28_fn, NULL);
SEG_END("CRT:main#026@L264");
SEG_BEGIN("CRT:main#027@L265");
    pthread_create(&t29, NULL, thread29_fn, NULL);
SEG_END("CRT:main#027@L265");
SEG_BEGIN("CRT:main#028@L266");
    pthread_create(&t30, NULL, thread30_fn, NULL);
SEG_END("CRT:main#028@L266");
SEG_BEGIN("CRT:main#029@L267");
    pthread_create(&t31, NULL, thread31_fn, NULL);
SEG_END("CRT:main#029@L267");
SEG_BEGIN("CRT:main#030@L268");
    pthread_create(&t32, NULL, thread32_fn, NULL);
SEG_END("CRT:main#030@L268");
SEG_BEGIN("CRT:main#031@L269");
    pthread_create(&t33, NULL, thread33_fn, NULL);
SEG_END("CRT:main#031@L269");
SEG_BEGIN("CRT:main#032@L270");
    pthread_create(&t34, NULL, thread34_fn, NULL);
SEG_END("CRT:main#032@L270");
SEG_BEGIN("CRT:main#033@L271");
    pthread_create(&t35, NULL, thread35_fn, NULL);
SEG_END("CRT:main#033@L271");
SEG_BEGIN("CRT:main#034@L272");
    pthread_create(&t36, NULL, thread36_fn, NULL);
SEG_END("CRT:main#034@L272");
SEG_BEGIN("CRT:main#035@L273");
    pthread_create(&t37, NULL, thread37_fn, NULL);
SEG_END("CRT:main#035@L273");
SEG_BEGIN("CRT:main#036@L274");
    pthread_create(&t38, NULL, thread38_fn, NULL);
SEG_END("CRT:main#036@L274");
SEG_BEGIN("CRT:main#037@L275");
    pthread_create(&t39, NULL, thread39_fn, NULL);
SEG_END("CRT:main#037@L275");
SEG_BEGIN("CRT:main#038@L276");
    pthread_create(&t40, NULL, thread40_fn, NULL);
SEG_END("CRT:main#038@L276");
SEG_BEGIN("CRT:main#039@L277");
    pthread_create(&t41, NULL, thread41_fn, NULL);
SEG_END("CRT:main#039@L277");
SEG_BEGIN("CRT:main#040@L278");
    pthread_create(&t42, NULL, thread42_fn, NULL);
SEG_END("CRT:main#040@L278");
SEG_BEGIN("CRT:main#041@L279");
    pthread_create(&t43, NULL, thread43_fn, NULL);
SEG_END("CRT:main#041@L279");
SEG_BEGIN("CRT:main#042@L280");
    pthread_create(&t44, NULL, thread44_fn, NULL);
SEG_END("CRT:main#042@L280");
SEG_BEGIN("CRT:main#043@L281");
    pthread_create(&t45, NULL, thread45_fn, NULL);
SEG_END("CRT:main#043@L281");
SEG_BEGIN("CRT:main#044@L282");
    pthread_create(&t46, NULL, thread46_fn, NULL);
SEG_END("CRT:main#044@L282");
SEG_BEGIN("CRT:main#045@L283");
    pthread_create(&t47, NULL, thread47_fn, NULL);
SEG_END("CRT:main#045@L283");
SEG_BEGIN("CRT:main#046@L284");
    pthread_create(&t48, NULL, thread48_fn, NULL);
SEG_END("CRT:main#046@L284");
SEG_BEGIN("CRT:main#047@L285");
    pthread_create(&t49, NULL, thread49_fn, NULL);
SEG_END("CRT:main#047@L285");
SEG_BEGIN("THR:main#048@286-287");

    /* 统一回收 */
SEG_END("THR:main#048@286-287");
SEG_BEGIN("JON:main#049@L288");
    pthread_join(t0, NULL);
SEG_END("JON:main#049@L288");
SEG_BEGIN("JON:main#050@L289");
    pthread_join(t1, NULL);
SEG_END("JON:main#050@L289");
SEG_BEGIN("JON:main#051@L290");
    pthread_join(t2, NULL);
SEG_END("JON:main#051@L290");
SEG_BEGIN("JON:main#052@L291");
    pthread_join(t3, NULL);
SEG_END("JON:main#052@L291");
SEG_BEGIN("JON:main#053@L292");
    pthread_join(t4, NULL);
SEG_END("JON:main#053@L292");
SEG_BEGIN("JON:main#054@L293");
    pthread_join(t5, NULL);
SEG_END("JON:main#054@L293");
SEG_BEGIN("JON:main#055@L294");
    pthread_join(t6, NULL);
SEG_END("JON:main#055@L294");
SEG_BEGIN("JON:main#056@L295");
    pthread_join(t7, NULL);
SEG_END("JON:main#056@L295");
SEG_BEGIN("JON:main#057@L296");
    pthread_join(t8, NULL);
SEG_END("JON:main#057@L296");
SEG_BEGIN("JON:main#058@L297");
    pthread_join(t9, NULL);
SEG_END("JON:main#058@L297");
SEG_BEGIN("JON:main#059@L298");
    pthread_join(t10, NULL);
SEG_END("JON:main#059@L298");
SEG_BEGIN("JON:main#060@L299");
    pthread_join(t11, NULL);
SEG_END("JON:main#060@L299");
SEG_BEGIN("JON:main#061@L300");
    pthread_join(t12, NULL);
SEG_END("JON:main#061@L300");
SEG_BEGIN("JON:main#062@L301");
    pthread_join(t13, NULL);
SEG_END("JON:main#062@L301");
SEG_BEGIN("JON:main#063@L302");
    pthread_join(t14, NULL);
SEG_END("JON:main#063@L302");
SEG_BEGIN("JON:main#064@L303");
    pthread_join(t15, NULL);
SEG_END("JON:main#064@L303");
SEG_BEGIN("JON:main#065@L304");
    pthread_join(t16, NULL);
SEG_END("JON:main#065@L304");
SEG_BEGIN("JON:main#066@L305");
    pthread_join(t17, NULL);
SEG_END("JON:main#066@L305");
SEG_BEGIN("JON:main#067@L306");
    pthread_join(t18, NULL);
SEG_END("JON:main#067@L306");
SEG_BEGIN("JON:main#068@L307");
    pthread_join(t19, NULL);
SEG_END("JON:main#068@L307");
SEG_BEGIN("JON:main#069@L308");
    pthread_join(t20, NULL);
SEG_END("JON:main#069@L308");
SEG_BEGIN("JON:main#070@L309");
    pthread_join(t21, NULL);
SEG_END("JON:main#070@L309");
SEG_BEGIN("JON:main#071@L310");
    pthread_join(t22, NULL);
SEG_END("JON:main#071@L310");
SEG_BEGIN("JON:main#072@L311");
    pthread_join(t23, NULL);
SEG_END("JON:main#072@L311");
SEG_BEGIN("JON:main#073@L312");
    pthread_join(t24, NULL);
SEG_END("JON:main#073@L312");
SEG_BEGIN("JON:main#074@L313");
    pthread_join(t25, NULL);
SEG_END("JON:main#074@L313");
SEG_BEGIN("JON:main#075@L314");
    pthread_join(t26, NULL);
SEG_END("JON:main#075@L314");
SEG_BEGIN("JON:main#076@L315");
    pthread_join(t27, NULL);
SEG_END("JON:main#076@L315");
SEG_BEGIN("JON:main#077@L316");
    pthread_join(t28, NULL);
SEG_END("JON:main#077@L316");
SEG_BEGIN("JON:main#078@L317");
    pthread_join(t29, NULL);
SEG_END("JON:main#078@L317");
SEG_BEGIN("JON:main#079@L318");
    pthread_join(t30, NULL);
SEG_END("JON:main#079@L318");
SEG_BEGIN("JON:main#080@L319");
    pthread_join(t31, NULL);
SEG_END("JON:main#080@L319");
SEG_BEGIN("JON:main#081@L320");
    pthread_join(t32, NULL);
SEG_END("JON:main#081@L320");
SEG_BEGIN("JON:main#082@L321");
    pthread_join(t33, NULL);
SEG_END("JON:main#082@L321");
SEG_BEGIN("JON:main#083@L322");
    pthread_join(t34, NULL);
SEG_END("JON:main#083@L322");
SEG_BEGIN("JON:main#084@L323");
    pthread_join(t35, NULL);
SEG_END("JON:main#084@L323");
SEG_BEGIN("JON:main#085@L324");
    pthread_join(t36, NULL);
SEG_END("JON:main#085@L324");
SEG_BEGIN("JON:main#086@L325");
    pthread_join(t37, NULL);
SEG_END("JON:main#086@L325");
SEG_BEGIN("JON:main#087@L326");
    pthread_join(t38, NULL);
SEG_END("JON:main#087@L326");
SEG_BEGIN("JON:main#088@L327");
    pthread_join(t39, NULL);
SEG_END("JON:main#088@L327");
SEG_BEGIN("JON:main#089@L328");
    pthread_join(t40, NULL);
SEG_END("JON:main#089@L328");
SEG_BEGIN("JON:main#090@L329");
    pthread_join(t41, NULL);
SEG_END("JON:main#090@L329");
SEG_BEGIN("JON:main#091@L330");
    pthread_join(t42, NULL);
SEG_END("JON:main#091@L330");
SEG_BEGIN("JON:main#092@L331");
    pthread_join(t43, NULL);
SEG_END("JON:main#092@L331");
SEG_BEGIN("JON:main#093@L332");
    pthread_join(t44, NULL);
SEG_END("JON:main#093@L332");
SEG_BEGIN("JON:main#094@L333");
    pthread_join(t45, NULL);
SEG_END("JON:main#094@L333");
SEG_BEGIN("JON:main#095@L334");
    pthread_join(t46, NULL);
SEG_END("JON:main#095@L334");
SEG_BEGIN("JON:main#096@L335");
    pthread_join(t47, NULL);
SEG_END("JON:main#096@L335");
SEG_BEGIN("JON:main#097@L336");
    pthread_join(t48, NULL);
SEG_END("JON:main#097@L336");
SEG_BEGIN("JON:main#098@L337");
    pthread_join(t49, NULL);
SEG_END("JON:main#098@L337");
SEG_BEGIN("THR:main#099@338-342");

    clock_gettime(CLOCK_MONOTONIC, &ts_prog_end);
    printf("Program total time: %.3fs\n", elapsed_seconds(&ts_prog_start, &ts_prog_end));
    puts("all threads done");
    return 0;
SEG_END("THR:main#099@338-342");
}
