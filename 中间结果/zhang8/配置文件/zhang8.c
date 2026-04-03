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
 * zhang8: 与 zhang2 同拓扑。busy_wait_seconds 用 nanosleep，参数 Cx 表示墙钟秒数（与 WORK_SCALE 无关）。
 * 注意：此版可能使 Pipeline Schedule 出现 SEG/MU 权重不一致；需跑通全流程时请改回与 zhang2 相同的循环版 busy_wait。
 */

#define C1  0.033
#define C2  0.44
#define C3  0.66
#define C4  0.033
#define C5  0.88
#define C6 20.0
#define C7  0.11
#define C8  0.066
#define C9  0.088
#define C10 0.11
#define C11 0.22
#define C12 0.11
#define C13 0.176
#define C14 0.176
#define C15 0.011
#define C16 2.0
#define F_LONG 28.0
#define F_SHORT 20.0

static void *worker_c0(void *arg);
static void *worker_c1(void *arg);
static void *worker_c2(void *arg);


#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];

static pthread_t thread_c0, thread_c1, thread_c2, thread_c3, thread_c4;

static sem_t sem_01;
static sem_t sem_02;
static sem_t sem_03;
static sem_t sem_04;
static sem_t sem_05;
static sem_t sem_06;

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
  if (seconds <= 0.0)
    seconds = 0.001;

  struct timespec ts;
  ts.tv_sec = (time_t)seconds;
  ts.tv_nsec = (long)((seconds - (double)ts.tv_sec) * 1000000000L);

  while (nanosleep(&ts, &ts) != 0)
  {
    if (errno != EINTR)
      break;
  }

  mat_c[0][0] += seconds;
}

static struct timespec prog_start_ts;

static void *worker_c2(void *arg)
{
  pthread_mutex_lock(&mutex_01);
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);
  sem_wait(&sem_02);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
  sem_wait(&sem_03);
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  return NULL;
}

static void *worker_c1(void *arg)
{
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  sem_wait(&sem_01);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  return NULL;
}

static void *worker_c0(void *arg)
{
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

int main(void)
{
  pthread_mutex_lock(&mutex_07);
  struct timespec prog_start_ts_local, prog_end_ts_local;
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(6, &cpu_set);
  CPU_SET(7, &cpu_set);

  if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0)
  {
    fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
  }
  init_matrices();
  clock_gettime(CLOCK_MONOTONIC, &prog_start_ts);
  clock_gettime(CLOCK_MONOTONIC, &prog_start_ts_local);
  if (sem_init(&sem_01, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_02, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_03, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_04, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_05, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_06, 0, 0) != 0)
    return 1;

  /* 启动关键链入口 + 填充任务 */
  /* 先创建填充任务，再创建关键链入口，便于 FIFO 先跑填充 */

  pthread_create(&thread_c0, NULL, worker_c0, NULL);
  pthread_create(&thread_c1, NULL, worker_c1, NULL);
  pthread_create(&thread_c2, NULL, worker_c2, NULL);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_07);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_08);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_09);
  sem_post(&sem_01);
  sem_post(&sem_02);
  pthread_join(thread_c0, NULL);
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_10);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_11);
  sem_post(&sem_03);
  pthread_join(thread_c1, NULL);
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_12);
  pthread_mutex_lock(&mutex_13);
  busy_wait_seconds(C14);
  pthread_mutex_unlock(&mutex_13);
  pthread_join(thread_c2, NULL);
  pthread_mutex_lock(&mutex_14);
  busy_wait_seconds(C15);
  pthread_mutex_unlock(&mutex_14);
  return 0;
}
