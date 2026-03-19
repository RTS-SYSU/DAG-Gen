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
#define C1 90.0
#define C2 2.0
#define C3 2.0
#define C4 90.0
#define C5 12.0
#define C6 100.0
#define C7 100.0
#define C8 12.0
#define C9 12.0
#define C10 140.0
#define C11 140.0
#define C12 12.0
#define C13 15.0
#define C14 100.0
#define C15 100.0
#define C16 15.0
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
static sem_t sem_07;
static sem_t sem_08;
static sem_t sem_09;
static sem_t sem_10;
static sem_t sem_11;
static sem_t sem_12;
static sem_t sem_13;
static sem_t sem_14;
static sem_t sem_15;
static sem_t sem_16;
static sem_t sem_17;
static sem_t sem_18;

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
static pthread_mutex_t mutex_17 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_18 = PTHREAD_MUTEX_INITIALIZER;

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
  l1_set_thread_prio_fifo(89);
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  sem_post(&sem_16);
  pthread_mutex_unlock(&mutex_07);
  l1_set_thread_prio_fifo(88);
  pthread_mutex_lock(&mutex_08);
  sem_wait(&sem_13);
  busy_wait_seconds(C7);
  sem_post(&sem_17);
  pthread_mutex_unlock(&mutex_08);
  l1_set_thread_prio_fifo(87);
  pthread_mutex_lock(&mutex_09);
  sem_wait(&sem_14);
  busy_wait_seconds(C7);
  sem_post(&sem_18);
  pthread_mutex_unlock(&mutex_09);
  l1_set_thread_prio_fifo(84);
  pthread_mutex_lock(&mutex_10);
  sem_wait(&sem_15);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_10);
  return NULL;
}

static void *worker_c1(void *arg) {
  l1_set_thread_prio_fifo(93);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C7);
  sem_post(&sem_10);
  sem_post(&sem_13);
  pthread_mutex_unlock(&mutex_11);
  l1_set_thread_prio_fifo(92);
  pthread_mutex_lock(&mutex_12);
  sem_wait(&sem_07);
  sem_wait(&sem_16);
  busy_wait_seconds(C7);
  sem_post(&sem_11);
  sem_post(&sem_14);
  pthread_mutex_unlock(&mutex_12);
  l1_set_thread_prio_fifo(86);
  pthread_mutex_lock(&mutex_13);
  sem_wait(&sem_08);
  sem_wait(&sem_17);
  busy_wait_seconds(C7);
  sem_post(&sem_12);
  sem_post(&sem_15);
  pthread_mutex_unlock(&mutex_13);
  l1_set_thread_prio_fifo(85);
  pthread_mutex_lock(&mutex_14);
  sem_wait(&sem_09);
  sem_wait(&sem_18);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_14);
  return NULL;
}

static void *worker_c0(void *arg) {
  l1_set_thread_prio_fifo(98);
  pthread_mutex_lock(&mutex_15);
  busy_wait_seconds(C7);
  sem_post(&sem_04);
  sem_post(&sem_07);
  pthread_mutex_unlock(&mutex_15);
  l1_set_thread_prio_fifo(97);
  pthread_mutex_lock(&mutex_16);
  sem_wait(&sem_01);
  sem_wait(&sem_10);
  busy_wait_seconds(C7);
  sem_post(&sem_05);
  sem_post(&sem_08);
  pthread_mutex_unlock(&mutex_16);
  l1_set_thread_prio_fifo(91);
  pthread_mutex_lock(&mutex_17);
  sem_wait(&sem_02);
  sem_wait(&sem_11);
  busy_wait_seconds(C7);
  sem_post(&sem_06);
  sem_post(&sem_09);
  pthread_mutex_unlock(&mutex_17);
  l1_set_thread_prio_fifo(83);
  pthread_mutex_lock(&mutex_18);
  sem_wait(&sem_03);
  sem_wait(&sem_12);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_18);
  return NULL;
}

int main(void) {
  l1_set_thread_prio_fifo(99);
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
  if (sem_init(&sem_07, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_08, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_09, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_10, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_11, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_12, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_13, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_14, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_15, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_16, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_17, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_18, 0, 0) != 0)
    return 1;

  /* 启动关键链入口 + 填充任务 */
  /* 先创建填充任务，再创建关键链入口，便于 FIFO 先跑填充 */
  busy_wait_seconds(C10);
  pthread_create(&thread_c0, NULL, worker_c0, NULL);
  pthread_create(&thread_c1, NULL, worker_c1, NULL);
  pthread_create(&thread_c2, NULL, worker_c2, NULL);
  pthread_mutex_unlock(&mutex_01);
  l1_set_thread_prio_fifo(96);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C10);
  sem_post(&sem_01);
  pthread_mutex_unlock(&mutex_02);
  l1_set_thread_prio_fifo(95);
  pthread_mutex_lock(&mutex_03);
  sem_wait(&sem_04);
  busy_wait_seconds(C10);
  sem_post(&sem_02);
  pthread_mutex_unlock(&mutex_03);
  l1_set_thread_prio_fifo(94);
  pthread_mutex_lock(&mutex_04);
  sem_wait(&sem_05);
  busy_wait_seconds(C10);
  sem_post(&sem_03);
  pthread_mutex_unlock(&mutex_04);
  l1_set_thread_prio_fifo(90);
  pthread_mutex_lock(&mutex_05);
  sem_wait(&sem_06);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_05);
  l1_set_thread_prio_fifo(82);
  pthread_mutex_lock(&mutex_06);
  pthread_join(thread_c0, NULL);
  pthread_join(thread_c1, NULL);
  pthread_join(thread_c2, NULL);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_06);
  return 0;
}
