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
  l1_set_thread_prio_fifo(90);
  pthread_mutex_lock(&mutex_01);
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);
  l1_set_thread_prio_fifo(89);
  sem_wait(&sem_02);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
  l1_set_thread_prio_fifo(87);
  sem_wait(&sem_03);
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  return NULL;
}

static void *worker_c1(void *arg)
{
  l1_set_thread_prio_fifo(96);
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  l1_set_thread_prio_fifo(95);
  sem_wait(&sem_01);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  return NULL;
}

static void *worker_c0(void *arg)
{
  l1_set_thread_prio_fifo(94);
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

int main(void)
{
  l1_set_thread_prio_fifo(99);
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
  pthread_mutex_unlock(&mutex_07);
  l1_set_thread_prio_fifo(98);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_08);
  l1_set_thread_prio_fifo(97);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_09);
  sem_post(&sem_01);
  sem_post(&sem_02);
  l1_set_thread_prio_fifo(93);
  pthread_join(thread_c0, NULL);
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_10);
  l1_set_thread_prio_fifo(92);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_11);
  sem_post(&sem_03);
  l1_set_thread_prio_fifo(91);
  pthread_join(thread_c1, NULL);
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_12);
  l1_set_thread_prio_fifo(88);
  pthread_mutex_lock(&mutex_13);
  busy_wait_seconds(C14);
  pthread_mutex_unlock(&mutex_13);
  l1_set_thread_prio_fifo(86);
  pthread_join(thread_c2, NULL);
  pthread_mutex_lock(&mutex_14);
  busy_wait_seconds(C15);
  pthread_mutex_unlock(&mutex_14);
  return 0;
}
