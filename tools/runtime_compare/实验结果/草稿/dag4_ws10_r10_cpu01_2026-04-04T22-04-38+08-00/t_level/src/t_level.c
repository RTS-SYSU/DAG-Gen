#define _GNU_SOURCE
#include "prio_runtime.h"
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * dag4: Gaussian Elimination DAG, chi = 6 (6x6 logical stage graph).
 *
 * 6 column threads = 6 runnable compute threads  >>  4 cores  =>  persistent
 * scheduling contention whenever multiple columns are in MU busy_wait.
 *
 * Task model (standard parallel GE benchmark):
 *   P(k,k)           pivot at stage k
 *   E(k,j)  j>k      elimination on column j at stage k
 *
 * Dependencies:
 *   E(0,j)   needs P(0,0)
 *   P(1,1)   needs E(0,1)
 *   E(1,j)   needs P(1,1) and E(0,j)   (E(0,j) same column, sequential)
 *   P(2,2)   needs E(1,2)
 *   ... and so on through P(5,5) after E(4,5)
 *
 * Column j executes, in order, all tasks in column j:
 *   j=0: P(0,0)
 *   j=1: E(0,1) P(1,1)
 *   j=2: E(0,2) E(1,2) P(2,2)
 *   j=3: E*(0..2,3) P(3,3)
 *   j=4: E*(0..3,4) P(4,4)
 *   j=5: E*(0..4,5) P(5,5)
 *
 * Semaphores after pivots (fan-out to columns j>k only):
 *   P(0,0) -> 5 posts   cols 1..5 start E(0,*)
 *   P(1,1) -> 4 posts
 *   P(2,2) -> 3 posts
 *   P(3,3) -> 2 posts
 *   P(4,4) -> 1 post    col5 starts E(4,5)
 *
 * Critical path (longest precedence chain, "diagonal front"):
 *   P00->E01->P11->E12->P22->E23->P33->E34->P44->E45->P55
 *   (11 heavy MU blocks)
 *
 * Off-critical parallel elimination (10 lighter MU blocks):
 *   E02,E03,E04,E05, E13,E14,E15, E24,E25, E35
 *
 * Weight policy (tunable):
 *   W_CRIT_HI on P(0,0)  — strongest single pivot (wcet / tie-break)
 *   W_CRIT on other 10 critical-chain nodes
 *   W_OFF on off-path elim — low so many threads stay runnable and
 *                            CFS dilutes everyone; algorithms prioritise
 *                            critical columns' MU blocks (col0..left chain).
 *
 * pthread_create order: col5..col0  — hurts FIFO(99): tail columns start first.
 *
 * Total: main x2 MU + 21 worker MU = 23 mutexes, 5 semaphores.
 */

#define C1    0.1    /* main#001 init */
#define C2    0.1    /* main#002 final */

/* Critical-chain nodes (heavy): longest path + diagonal pivots / elim on front */
#define C3    5.5    /* P(0,0)        — head pivot, heaviest */
#define C4    4.5    /* E(0,1) */
#define C5    4.5    /* P(1,1) */
#define C7    4.5    /* E(1,2) */
#define C8    4.5    /* P(2,2) */
#define C11   4.5    /* E(2,3) */
#define C12   4.5    /* P(3,3) */
#define C16   4.5    /* E(3,4) */
#define C17   4.5    /* P(4,4) */
#define C22   4.5    /* E(4,5) */
#define C23   4.5    /* P(5,5) */

/* Off-path elimination (light): extra parallelism, lengthens contention window */
#define C6    0.9    /* E(0,2) */
#define C9    0.9    /* E(0,3) */
#define C10   0.9    /* E(1,3) */
#define C13   0.9    /* E(0,4) */
#define C14   0.9    /* E(1,4) */
#define C15   0.9    /* E(2,4) */
#define C18   0.9    /* E(0,5) */
#define C19   0.9    /* E(1,5) */
#define C20   0.9    /* E(2,5) */
#define C21   0.9    /* E(3,5) */

#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];
volatile double g_busy_sink = 0.0;

static void init_matrices(void) {
  for (int i = 0; i < MAT_N; i++)
    for (int j = 0; j < MAT_N; j++) {
      mat_a[i][j] = (double)(i + j) * 0.001;
      mat_b[i][j] = (double)(i - j) * 0.001;
    }
}

static void busy_wait_seconds(double seconds) {
  int units = (int)(seconds * WORK_SCALE + 0.5);
  for (int u = 0; u < units; u++) {
    for (int i = 0; i < MAT_N; i++)
      for (int j = 0; j < MAT_N; j++) {
        double s = 0.0;
        for (int k = 0; k < MAT_N; k++)
          s += mat_a[i][k] * mat_b[k][j];
        mat_c[i][j] = s;
      }
  }
  g_busy_sink += mat_c[0][0];
}

/* mutex_01..02: main ; mutex_03..23: GE tasks (21 blocks) */
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
static pthread_mutex_t mutex_19 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_20 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_21 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_22 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_23 = PTHREAD_MUTEX_INITIALIZER;

static sem_t sem_ge_p0;
static sem_t sem_ge_p1;
static sem_t sem_ge_p2;
static sem_t sem_ge_p3;
static sem_t sem_ge_p4;

static pthread_t t_col0, t_col1, t_col2, t_col3, t_col4, t_col5;

static void *worker_col0(void *arg);
static void *worker_col1(void *arg);
static void *worker_col2(void *arg);
static void *worker_col3(void *arg);
static void *worker_col4(void *arg);
static void *worker_col5(void *arg);

static void *worker_col0(void *arg) {
  l1_set_thread_prio_fifo(82);
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  sem_post(&sem_ge_p0);
  sem_post(&sem_ge_p0);
  sem_post(&sem_ge_p0);
  sem_post(&sem_ge_p0);
  sem_post(&sem_ge_p0);
  return NULL;
}

static void *worker_col1(void *arg) {
  l1_set_thread_prio_fifo(81);
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  l1_set_thread_prio_fifo(89);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  sem_post(&sem_ge_p1);
  sem_post(&sem_ge_p1);
  sem_post(&sem_ge_p1);
  sem_post(&sem_ge_p1);
  return NULL;
}

static void *worker_col2(void *arg) {
  l1_set_thread_prio_fifo(80);
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);
  l1_set_thread_prio_fifo(84);
  sem_wait(&sem_ge_p1);
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);
  l1_set_thread_prio_fifo(92);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_08);
  sem_post(&sem_ge_p2);
  sem_post(&sem_ge_p2);
  sem_post(&sem_ge_p2);
  return NULL;
}

static void *worker_col3(void *arg) {
  l1_set_thread_prio_fifo(79);
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_09);
  l1_set_thread_prio_fifo(83);
  sem_wait(&sem_ge_p1);
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_10);
  l1_set_thread_prio_fifo(86);
  sem_wait(&sem_ge_p2);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_11);
  l1_set_thread_prio_fifo(91);
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_12);
  sem_post(&sem_ge_p3);
  sem_post(&sem_ge_p3);
  return NULL;
}

static void *worker_col4(void *arg) {
  l1_set_thread_prio_fifo(78);
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_13);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_13);
  l1_set_thread_prio_fifo(85);
  sem_wait(&sem_ge_p1);
  pthread_mutex_lock(&mutex_14);
  busy_wait_seconds(C14);
  pthread_mutex_unlock(&mutex_14);
  l1_set_thread_prio_fifo(87);
  sem_wait(&sem_ge_p2);
  pthread_mutex_lock(&mutex_15);
  busy_wait_seconds(C15);
  pthread_mutex_unlock(&mutex_15);
  l1_set_thread_prio_fifo(88);
  sem_wait(&sem_ge_p3);
  pthread_mutex_lock(&mutex_16);
  busy_wait_seconds(C16);
  pthread_mutex_unlock(&mutex_16);
  l1_set_thread_prio_fifo(94);
  pthread_mutex_lock(&mutex_17);
  busy_wait_seconds(C17);
  pthread_mutex_unlock(&mutex_17);
  sem_post(&sem_ge_p4);
  return NULL;
}

static void *worker_col5(void *arg) {
  l1_set_thread_prio_fifo(90);
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_18);
  busy_wait_seconds(C18);
  pthread_mutex_unlock(&mutex_18);
  l1_set_thread_prio_fifo(93);
  sem_wait(&sem_ge_p1);
  pthread_mutex_lock(&mutex_19);
  busy_wait_seconds(C19);
  pthread_mutex_unlock(&mutex_19);
  l1_set_thread_prio_fifo(95);
  sem_wait(&sem_ge_p2);
  pthread_mutex_lock(&mutex_20);
  busy_wait_seconds(C20);
  pthread_mutex_unlock(&mutex_20);
  l1_set_thread_prio_fifo(96);
  sem_wait(&sem_ge_p3);
  pthread_mutex_lock(&mutex_21);
  busy_wait_seconds(C21);
  pthread_mutex_unlock(&mutex_21);
  l1_set_thread_prio_fifo(97);
  sem_wait(&sem_ge_p4);
  pthread_mutex_lock(&mutex_22);
  busy_wait_seconds(C22);
  pthread_mutex_unlock(&mutex_22);
  l1_set_thread_prio_fifo(98);
  pthread_mutex_lock(&mutex_23);
  busy_wait_seconds(C23);
  pthread_mutex_unlock(&mutex_23);
  return NULL;
}

int main(void) {
    struct timespec ts_main_begin, ts_main_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);
  l1_set_thread_prio_fifo(77);
  pthread_mutex_lock(&mutex_01);
  init_matrices();
  if (sem_init(&sem_ge_p0, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_ge_p1, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_ge_p2, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_ge_p3, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_ge_p4, 0, 0) != 0)
    return 1;
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);

  /* tail columns first: bad for FIFO equal-prio, good for ranked algos once prio injected */
  pthread_create(&t_col5, NULL, worker_col5, NULL);
  pthread_create(&t_col4, NULL, worker_col4, NULL);
  pthread_create(&t_col3, NULL, worker_col3, NULL);
  pthread_create(&t_col2, NULL, worker_col2, NULL);
  pthread_create(&t_col1, NULL, worker_col1, NULL);
  pthread_create(&t_col0, NULL, worker_col0, NULL);

  l1_set_thread_prio_fifo(99);
  pthread_join(t_col0, NULL);
  pthread_join(t_col1, NULL);
  pthread_join(t_col2, NULL);
  pthread_join(t_col3, NULL);
  pthread_join(t_col4, NULL);
  pthread_join(t_col5, NULL);

  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);
    {
        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)
            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;
        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\n", main_s);
    }
  return 0;
}
