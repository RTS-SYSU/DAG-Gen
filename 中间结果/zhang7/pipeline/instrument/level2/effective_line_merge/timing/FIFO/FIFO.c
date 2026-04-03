#define _GNU_SOURCE
#include "prio_runtime.h"
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * zhang7: 6 线程 (main + critical + filler_a/b/c/d), 纯 fork/join, 0 sem
 *
 * 设计目标: 让 zhao2020/heft/wcet_first/t_level 的 avg_s 明显优于 CFS
 *
 * 核心策略:
 *   - critical 线程: 1 个 MU 块, 权重最大(C2=800), 是关键路径
 *   - 4 个 filler 线程: 各 1 个 MU 块, 权重中等(C3~C6=250 each, 总 1000)
 *   - main: 极轻(C1=1, C7=1), 只做 fork/join
 *   - 5 个 worker 竞争 2 核
 *
 * 2 核下时间推演:
 *   算法: critical(prio=最高) 独占 1 核, 4 个 filler 共享另 1 核
 *         critical 耗时 = 800 单位
 *         filler 串行 = 250*4 = 1000 单位
 *         总时间 = max(800, 1000) = 1000 单位
 *
 *   CFS: 5 线程均分 2 核, critical 得 2/5 核 = 0.4 核
 *        critical 耗时 = 800/0.4 = 2000 单位
 *        总时间 ≈ 2000 单位 (瓶颈是 critical)
 *
 *   预期差距: 2000/1000 = 2x, 算法快 50%
 *
 * 为什么每个 worker 只有 1 个 MU 块:
 *   避免 pipeline 切分后第二段优先级降低被 filler 抢占 (zhang5 v3 的教训)
 *
 * 为什么 0 个 sem:
 *   避免 SEG 段产生零权重节点干扰优先级计算
 *
 * 为什么 filler 总量 > critical:
 *   确保 filler 不会比 critical 先完成, 否则后半段只剩 critical 独占 2 核,
 *   CFS 和算法没有差异
 */

#define C1  1.0     /* main#001: 极轻, fork 前 */
#define C2  800.0   /* critical#001: 关键路径, 最重 */
#define C3  250.0   /* filler_a#001: 填充 */
#define C4  250.0   /* filler_b#001: 填充 */
#define C5  250.0   /* filler_c#001: 填充 */
#define C6  250.0   /* filler_d#001: 填充 */
#define C7  1.0     /* main#002: 极轻, 收尾 */

static void *critical_fn(void *arg);
static void *filler_a(void *arg);
static void *filler_b(void *arg);
static void *filler_c(void *arg);
static void *filler_d(void *arg);

#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];

static volatile double g_busy_sink = 0.0;

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

/* --- 同步原语: 全部自锁, 无竞争, 按顺序命名 --- */
static pthread_mutex_t mutex_01 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_02 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_03 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_04 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_05 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_06 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_07 = PTHREAD_MUTEX_INITIALIZER;

static pthread_t thread_crit, thread_fa, thread_fb, thread_fc, thread_fd;

/* --- critical: C2=800 (关键路径, 1 个 MU 块) --- */
static void *critical_fn(void *arg)
{
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
  return NULL;
}

/* --- filler_a: C3=250 --- */
static void *filler_a(void *arg)
{
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  return NULL;
}

/* --- filler_b: C4=250 --- */
static void *filler_b(void *arg)
{
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  return NULL;
}

/* --- filler_c: C5=250 --- */
static void *filler_c(void *arg)
{
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  return NULL;
}

/* --- filler_d: C6=250 --- */
static void *filler_d(void *arg)
{
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

/* --- main --- */
int main(void)
{
    struct timespec ts_main_begin, ts_main_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);
    l1_set_thread_prio_fifo(99);
  pthread_mutex_lock(&mutex_01);
  init_matrices();
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);
  pthread_create(&thread_fa, NULL, filler_a, NULL);
  pthread_create(&thread_fb, NULL, filler_b, NULL);
  pthread_create(&thread_fc, NULL, filler_c, NULL);
  pthread_create(&thread_fd, NULL, filler_d, NULL);
  pthread_create(&thread_crit, NULL, critical_fn, NULL);
  pthread_join(thread_crit, NULL);
  pthread_join(thread_fa, NULL);
  pthread_join(thread_fb, NULL);
  pthread_join(thread_fc, NULL);
  pthread_join(thread_fd, NULL);
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);
    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);
    {
        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)
            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;
        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\n", main_s);
    }
  return 0;
}