#define _GNU_SOURCE
#include <errno.h>
#include "segtrace.h"
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define C1 350.0
#define C2 8.0
#define C3 8.0
#define C4 220.0
#define C5 4.0
#define C6 1.0
#define C7 1.0
#define C8 1.0
#define C9 2.0
#define C10 140.0
#define C11 80.0
#define C12 100.0
#define C13 50.0
#define C14 80.0
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

SEG_BEGIN("MU:worker_c2#001@98-100");
  pthread_mutex_lock(&mutex_01);
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);
SEG_END("MU:worker_c2#001@98-100");
SEG_BEGIN("MU:worker_c2#002@101-104");
  pthread_mutex_lock(&mutex_02);
  sem_wait(&sem_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
SEG_END("MU:worker_c2#002@101-104");
SEG_BEGIN("MU:worker_c2#003@105-108");
  pthread_mutex_lock(&mutex_03);
  sem_wait(&sem_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
SEG_END("MU:worker_c2#003@105-108");
  return NULL;
}

static void *worker_c1(void *arg) {
SEG_BEGIN("MU:worker_c1#001@113-115");
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
SEG_END("MU:worker_c1#001@113-115");
SEG_BEGIN("MU:worker_c1#002@116-119");
  pthread_mutex_lock(&mutex_05);
  sem_wait(&sem_01);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
SEG_END("MU:worker_c1#002@116-119");
  return NULL;
}

static void *worker_c0(void *arg) {

SEG_BEGIN("MU:worker_c0#001@125-127");
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_07);
SEG_END("MU:worker_c0#001@125-127");
  return NULL;
}

int main(void) {
  const char *__seg_dir = getenv("SEGTRACE_DIR");
  if (__seg_dir && __seg_dir[0])
    segtrace_init(__seg_dir);
SEG_BEGIN("MU:main#001@132-168");
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
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_01);
SEG_END("MU:main#001@132-168");
SEG_BEGIN("MU:main#002@169-171");
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_07);
SEG_END("MU:main#002@169-171");
SEG_BEGIN("MU:main#003@172-176");
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C9);
  sem_post(&sem_01);
  sem_post(&sem_02);
  pthread_mutex_unlock(&mutex_08);
SEG_END("MU:main#003@172-176");
SEG_BEGIN("MU:main#004@177-180");
  pthread_mutex_lock(&mutex_09);
  pthread_join(thread_c0, NULL);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_09);
SEG_END("MU:main#004@177-180");
SEG_BEGIN("MU:main#005@181-184");
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C11);
  sem_post(&sem_03);
  pthread_mutex_unlock(&mutex_10);
SEG_END("MU:main#005@181-184");
SEG_BEGIN("MU:main#006@185-188");
  pthread_mutex_lock(&mutex_11);
  pthread_join(thread_c1, NULL);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_11);
SEG_END("MU:main#006@185-188");
SEG_BEGIN("MU:main#007@189-191");
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_12);
SEG_END("MU:main#007@189-191");
SEG_BEGIN("MU:main#008@192-195");
  pthread_mutex_lock(&mutex_13);
  pthread_join(thread_c2, NULL);
  busy_wait_seconds(C14);
  pthread_mutex_unlock(&mutex_13);
SEG_END("MU:main#008@192-195");
  return 0;
}
