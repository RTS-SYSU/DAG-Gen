#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * zhang8: 6 线程 (main + critical + filler_a/b/c/d), 纯 fork/join, 0 sem
 * 修改版本：使用固定时间等待替代 busy_wait，用于纯调度研究
 * 计算耗时干扰已排除，所有节点使用固定延时
 *
 * 设计目标: 让 zhao2020/heft/wcet_first/t_level 的 avg_s 明显优于 CFS
 * 总运行时间目标: 1~3 秒/轮
 *
 * 当前配置：
 *   - critical(C2): 1.5s (关键路径)
 *   - 4 个 filler(C3~C6): 0.6s each
 *   - main: 极轻 (0.05s)
 */

#define C1  0.05    /* main#001: 极轻, fork 前 */
#define C2  1.50    /* critical#001: 关键路径, 最重 (1.5秒) */
#define C3  0.60    /* filler_a#001: 填充 (0.6秒) */
#define C4  0.60    /* filler_b#001: 填充 (0.6秒) */
#define C5  0.60    /* filler_c#001: 填充 (0.6秒) */
#define C6  0.60    /* filler_d#001: 填充 (0.6秒) */
#define C7  0.05    /* main#002: 极轻, 收尾 */

static void *critical_fn(void *arg);
static void *filler_a(void *arg);
static void *filler_b(void *arg);
static void *filler_c(void *arg);
static void *filler_d(void *arg);

#define MAT_N 64
static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];

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

/* 固定时间等待函数 - 用于纯调度研究，排除计算耗时干扰 */
static void fixed_wait_seconds(double seconds)
{
  if (seconds <= 0.0) seconds = 0.01;
  struct timespec ts;
  ts.tv_sec = (time_t)seconds;
  ts.tv_nsec = (long)((seconds - (double)ts.tv_sec) * 1000000000L);
  nanosleep(&ts, NULL);
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
  fixed_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
  return NULL;
}

/* --- filler_a: C3=0.6s --- */
static void *filler_a(void *arg)
{
  pthread_mutex_lock(&mutex_03);
  fixed_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  return NULL;
}

/* --- filler_b: C4=0.6s --- */
static void *filler_b(void *arg)
{
  pthread_mutex_lock(&mutex_04);
  fixed_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  return NULL;
}

/* --- filler_c: C5=0.6s --- */
static void *filler_c(void *arg)
{
  pthread_mutex_lock(&mutex_05);
  fixed_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  return NULL;
}

/* --- filler_d: C6=0.6s --- */
static void *filler_d(void *arg)
{
  pthread_mutex_lock(&mutex_06);
  fixed_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

/* --- main --- */
int main(void)
{
  pthread_mutex_lock(&mutex_01);
  init_matrices();                  /* Pipeline DAG parser 需要此调用 */
  fixed_wait_seconds(C1);           /* 极轻启动延时 */
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
  fixed_wait_seconds(C7);           /* 极轻收尾延时 */
  pthread_mutex_unlock(&mutex_07);

  printf("zhang8 (fixed delay) completed (~1.6s). Used for pure scheduling research.\n");
  return 0;
}