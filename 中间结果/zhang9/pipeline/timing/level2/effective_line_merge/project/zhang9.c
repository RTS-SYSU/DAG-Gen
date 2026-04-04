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
#define C1 1.0
#define C2 1.0
#define C3 1.0
#define C4 1.0
#define C5 600.0
#define C6 20.0
#define C7 500.0
#define C8 2.0
#define C9 2.0
#define C10 2.0
#define C11 2.0
#define C12 2.0
#define C13 2.0
#define C14 2.0
#define C15 1.0
#define C16 2.0

static void *worker_c0(void *arg);
static void *worker_c1(void *arg);
static void *worker_c2(void *arg);

#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

#define busy_wait_seconds(weight) \
  do { \
    unsigned long long _bw_freq, _bw_start, _bw_now; \
    __asm__ __volatile__("mrs %0, cntfrq_el0" : "=r"(_bw_freq)); \
    unsigned long long _bw_ticks = (unsigned long long)((weight) * WORK_SCALE * 1e-5 * (double)_bw_freq); \
    __asm__ __volatile__("mrs %0, cntvct_el0" : "=r"(_bw_start)); \
    for (;;) { \
      __asm__ __volatile__("mrs %0, cntvct_el0" : "=r"(_bw_now)); \
      if (_bw_now - _bw_start >= _bw_ticks) break; \
    } \
  } while (0)

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

static struct timespec prog_start_ts;

static void *worker_c2(void *arg)
{
  pthread_mutex_lock(&mutex_01);
SEG_BEGIN("MU:worker_c2#001@77-79");
  busy_wait_seconds(C1);
SEG_END("MU:worker_c2#001@77-79");
  pthread_mutex_unlock(&mutex_01);
  sem_wait(&sem_02);
  pthread_mutex_lock(&mutex_02);
SEG_BEGIN("MU:worker_c2#002@80-83");
  busy_wait_seconds(C2);
SEG_END("MU:worker_c2#002@80-83");
  pthread_mutex_unlock(&mutex_02);
  sem_wait(&sem_03);
  pthread_mutex_lock(&mutex_03);
SEG_BEGIN("MU:worker_c2#003@84-87");
  busy_wait_seconds(C3);
SEG_END("MU:worker_c2#003@84-87");
  pthread_mutex_unlock(&mutex_03);
  return NULL;
}

static void *worker_c1(void *arg)
{
  pthread_mutex_lock(&mutex_04);
SEG_BEGIN("MU:worker_c1#001@93-95");
  busy_wait_seconds(C4);
SEG_END("MU:worker_c1#001@93-95");
  pthread_mutex_unlock(&mutex_04);
  sem_wait(&sem_01);
  pthread_mutex_lock(&mutex_05);
SEG_BEGIN("MU:worker_c1#002@96-99");
  busy_wait_seconds(C5);
SEG_END("MU:worker_c1#002@96-99");
  pthread_mutex_unlock(&mutex_05);
  return NULL;
}

static void *worker_c0(void *arg)
{
  pthread_mutex_lock(&mutex_06);
SEG_BEGIN("MU:worker_c0#001@105-107");
  busy_wait_seconds(C7);
SEG_END("MU:worker_c0#001@105-107");
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

int main(void)
{
  pthread_mutex_lock(&mutex_07);
SEG_BEGIN("MU:main#001@113-143");
  struct timespec prog_start_ts_local, prog_end_ts_local;
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(6, &cpu_set);
  CPU_SET(7, &cpu_set);

  if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0)
  {
    fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
  }
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

  pthread_create(&thread_c0, NULL, worker_c0, NULL);
  pthread_create(&thread_c1, NULL, worker_c1, NULL);
  pthread_create(&thread_c2, NULL, worker_c2, NULL);
  busy_wait_seconds(C8);
SEG_END("MU:main#001@113-143");
  pthread_mutex_unlock(&mutex_07);
  pthread_mutex_lock(&mutex_08);
SEG_BEGIN("MU:main#002@144-146");
  busy_wait_seconds(C9);
SEG_END("MU:main#002@144-146");
  pthread_mutex_unlock(&mutex_08);
  pthread_mutex_lock(&mutex_09);
SEG_BEGIN("MU:main#003@147-151");
  busy_wait_seconds(C10);
SEG_END("MU:main#003@147-151");
  pthread_mutex_unlock(&mutex_09);
  sem_post(&sem_01);
  sem_post(&sem_02);
  pthread_join(thread_c0, NULL);
  pthread_mutex_lock(&mutex_10);
SEG_BEGIN("MU:main#004@152-155");
  busy_wait_seconds(C11);
SEG_END("MU:main#004@152-155");
  pthread_mutex_unlock(&mutex_10);
  pthread_mutex_lock(&mutex_11);
SEG_BEGIN("MU:main#005@156-159");
  busy_wait_seconds(C12);
SEG_END("MU:main#005@156-159");
  pthread_mutex_unlock(&mutex_11);
  sem_post(&sem_03);
  pthread_join(thread_c1, NULL);
  pthread_mutex_lock(&mutex_12);
SEG_BEGIN("MU:main#006@160-163");
  busy_wait_seconds(C13);
SEG_END("MU:main#006@160-163");
  pthread_mutex_unlock(&mutex_12);
  pthread_mutex_lock(&mutex_13);
SEG_BEGIN("MU:main#007@164-166");
  busy_wait_seconds(C14);
SEG_END("MU:main#007@164-166");
  pthread_mutex_unlock(&mutex_13);
  pthread_join(thread_c2, NULL);
  pthread_mutex_lock(&mutex_14);
SEG_BEGIN("MU:main#008@167-170");
  busy_wait_seconds(C15);
SEG_END("MU:main#008@167-170");
  pthread_mutex_unlock(&mutex_14);
  return 0;
}
