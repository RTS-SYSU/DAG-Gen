#define _GNU_SOURCE
#include "segtrace.h"
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define C1 70.0
#define C2 45.0
#define C3 60.0
#define C4 75.0
#define C5 55.0
#define C6 8.0
#define C7 80.0
#define C8 8.0
#define C9 8.0
#define C10 2.0
#define C11 2.0
#define C12 2.0
#define C13 2.0
#define C14 2.0
#define C15 2.0
#define C16 2.0
#define F_LONG 28.0
#define F_SHORT 20.0

static void *worker_c0(void *arg);
static void *worker_c1(void *arg);
static void *worker_c2(void *arg);
static void *worker_c3(void *arg);

#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 25000
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

static void init_matrices(void) {
  for (int i = 0; i < MAT_N; ++i) {
    for (int j = 0; j < MAT_N; ++j) {
      mat_a[i][j] = (double)(i + j + 1);
      mat_b[i][j] = (double)(i * 2 + j + 3);
      mat_c[i][j] = 0.0;
    }
  }
}

static void busy_wait_seconds(double seconds) {
  int repeat_count = (int)(seconds * WORK_SCALE * 0.1);
  if (repeat_count < 1)
    repeat_count = 1;
  for (int r = 0; r < repeat_count; ++r) {
    for (int i = 0; i < MAT_N; ++i) {
      for (int j = 0; j < MAT_N; ++j) {
        double accum = 0.0;
        for (int k = 0; k < MAT_N; ++k) {
          accum += mat_a[i][k] * mat_b[k][j];
        }
        mat_c[i][j] = accum;
      }
    }
  }
}

static struct timespec prog_start_ts;

static void *worker_c2(void *arg) {

SEG_BEGIN("MU:worker_c2#001@101-103");
  pthread_mutex_lock(&mutex_01);
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);
SEG_END("MU:worker_c2#001@101-103");
SEG_BEGIN("SEG:worker_c2#002@104-104");

SEG_END("SEG:worker_c2#002@104-104");
SEG_BEGIN("MU:worker_c2#003@105-108");
  pthread_mutex_lock(&mutex_02);
  sem_wait(&sem_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
SEG_END("MU:worker_c2#003@105-108");
SEG_BEGIN("SEG:worker_c2#004@109-109");

SEG_END("SEG:worker_c2#004@109-109");
SEG_BEGIN("MU:worker_c2#005@110-113");
  pthread_mutex_lock(&mutex_03);
  sem_wait(&sem_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
SEG_END("MU:worker_c2#005@110-113");
  return NULL;
}

static void *worker_c1(void *arg) {
SEG_BEGIN("MU:worker_c1#001@118-120");
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
SEG_END("MU:worker_c1#001@118-120");
SEG_BEGIN("SEG:worker_c1#002@121-121");

SEG_END("SEG:worker_c1#002@121-121");
SEG_BEGIN("MU:worker_c1#003@122-125");
  pthread_mutex_lock(&mutex_05);
  sem_wait(&sem_01);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
SEG_END("MU:worker_c1#003@122-125");
SEG_BEGIN("SEG:worker_c1#004@126-126");

SEG_END("SEG:worker_c1#004@126-126");
  return NULL;
}

static void *worker_c0(void *arg) {

SEG_BEGIN("MU:worker_c0#001@132-134");
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);
SEG_END("MU:worker_c0#001@132-134");
  return NULL;
}

int main(void) {
SEG_BEGIN("MU:main#001@139-175");
  pthread_mutex_lock(&mutex_01);
  struct timespec prog_start_ts_local, prog_end_ts_local;
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(0, &cpu_set);
  CPU_SET(1, &cpu_set);
  CPU_SET(2, &cpu_set);
  CPU_SET(3, &cpu_set);
  if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0) {
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
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_01);
SEG_END("MU:main#001@139-175");
SEG_BEGIN("MU:main#002@176-178");
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_07);
SEG_END("MU:main#002@176-178");
SEG_BEGIN("MU:main#003@179-183");
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C10);
  sem_post(&sem_01);
  sem_post(&sem_02);
  pthread_mutex_unlock(&mutex_08);
SEG_END("MU:main#003@179-183");
SEG_BEGIN("MU:main#004@184-187");
  pthread_mutex_lock(&mutex_09);
  pthread_join(thread_c0, NULL);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_09);
SEG_END("MU:main#004@184-187");
SEG_BEGIN("MU:main#005@188-191");
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C10);
  sem_post(&sem_03);
  pthread_mutex_unlock(&mutex_10);
SEG_END("MU:main#005@188-191");
SEG_BEGIN("MU:main#006@192-195");
  pthread_mutex_lock(&mutex_11);
  pthread_join(thread_c1, NULL);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_11);
SEG_END("MU:main#006@192-195");
SEG_BEGIN("MU:main#007@196-198");
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_12);
SEG_END("MU:main#007@196-198");
SEG_BEGIN("MU:main#008@199-202");
  pthread_mutex_lock(&mutex_13);
  pthread_join(thread_c2, NULL);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_13);
SEG_END("MU:main#008@199-202");
  return 0;
}
