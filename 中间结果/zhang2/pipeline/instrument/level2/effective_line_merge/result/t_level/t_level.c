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
#define C1 15.0
#define C2 200.0
#define C3 300.0
#define C4 15.0
#define C5 400.0
#define C6 20.0
#define C7 50.0
#define C8 30.0
#define C9 40.0
#define C10 50.0
#define C11 100.0
#define C12 50.0
#define C13 80.0
#define C14 80.0
#define C15 5.0
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

static volatile double g_busy_sink = 0.0;

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

static struct timespec prog_start_ts;

static void *worker_c2(void *arg)
{
  l1_set_thread_prio_fifo(87);
  pthread_mutex_lock(&mutex_01);
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);
  l1_set_thread_prio_fifo(92);
  sem_wait(&sem_02);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
  l1_set_thread_prio_fifo(96);
  sem_wait(&sem_03);
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  return NULL;
}

static void *worker_c1(void *arg)
{
  l1_set_thread_prio_fifo(88);
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  l1_set_thread_prio_fifo(93);
  sem_wait(&sem_01);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  return NULL;
}

static void *worker_c0(void *arg)
{
  l1_set_thread_prio_fifo(89);
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

int main(void)
{
  l1_set_thread_prio_fifo(86);
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
  l1_set_thread_prio_fifo(90);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_08);
  l1_set_thread_prio_fifo(91);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_09);
  sem_post(&sem_01);
  sem_post(&sem_02);
  l1_set_thread_prio_fifo(94);
  pthread_join(thread_c0, NULL);
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_10);
  l1_set_thread_prio_fifo(95);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_11);
  sem_post(&sem_03);
  l1_set_thread_prio_fifo(97);
  pthread_join(thread_c1, NULL);
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_12);
  l1_set_thread_prio_fifo(98);
  pthread_mutex_lock(&mutex_13);
  busy_wait_seconds(C14);
  pthread_mutex_unlock(&mutex_13);
  l1_set_thread_prio_fifo(99);
  pthread_join(thread_c2, NULL);
  pthread_mutex_lock(&mutex_14);
  busy_wait_seconds(C15);
  pthread_mutex_unlock(&mutex_14);
  return 0;
}
