#define _GNU_SOURCE
#include "segtrace.h"
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
 *   Strong crit vs off-path spread so measured avg_ns separates on the DAG;
 *   CPF/LPF/t_level priorities beat FIFO (same RT prio) and CFS (fair share).
 *
 * pthread_create order: col5..col0  — hurts FIFO(99): tail columns start first.
 *
 * Total: main x2 MU + 21 worker MU = 23 mutexes, 5 semaphores.
 */

#define C1    0.1    /* main#001 init */
#define C2    0.1    /* main#002 final */

/* Critical-chain nodes (heavy): longest path + diagonal pivots / elim on front */
#define C3    6.0    /* P(0,0) */
#define C4    4.8    /* E(0,1) */
#define C5    5.0    /* P(1,1) */
#define C7    5.0    /* E(1,2) */
#define C8    5.8    /* P(2,2) */
#define C11   6.8    /* E(2,3) */
#define C12   7.8    /* P(3,3) */
#define C16   9.0    /* E(3,4) */
#define C17   10.0   /* P(4,4) */
#define C22   12.0   /* E(4,5) */
#define C23   13.5   /* P(5,5) */

/* Off-path elimination: left side stay light; right side ramps up toward sink */
#define C6    0.30   /* E(0,2) */
#define C9    0.50   /* E(0,3) */
#define C10   0.70   /* E(1,3) */
#define C13   0.80   /* E(0,4) */
#define C14   1.00   /* E(1,4) */
#define C15   1.40   /* E(2,4) */
#define C18   4.50   /* E(0,5) */
#define C19   5.50   /* E(1,5) */
#define C20   7.00   /* E(2,5) */
#define C21   8.50   /* E(3,5) */

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
  pthread_mutex_lock(&mutex_03);
SEG_BEGIN("MU:worker_col0#001@158-165");
  busy_wait_seconds(C3);
SEG_END("MU:worker_col0#001@158-165");
  pthread_mutex_unlock(&mutex_03);
  sem_post(&sem_ge_p0);
  sem_post(&sem_ge_p0);
  sem_post(&sem_ge_p0);
  sem_post(&sem_ge_p0);
  sem_post(&sem_ge_p0);
  return NULL;
}

static void *worker_col1(void *arg) {
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_04);
SEG_BEGIN("MU:worker_col1#001@170-173");
  busy_wait_seconds(C4);
SEG_END("MU:worker_col1#001@170-173");
  pthread_mutex_unlock(&mutex_04);
  pthread_mutex_lock(&mutex_05);
SEG_BEGIN("MU:worker_col1#002@174-180");
  busy_wait_seconds(C5);
SEG_END("MU:worker_col1#002@174-180");
  pthread_mutex_unlock(&mutex_05);
  sem_post(&sem_ge_p1);
  sem_post(&sem_ge_p1);
  sem_post(&sem_ge_p1);
  sem_post(&sem_ge_p1);
  return NULL;
}

static void *worker_col2(void *arg) {
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_06);
SEG_BEGIN("MU:worker_col2#001@185-188");
  busy_wait_seconds(C6);
SEG_END("MU:worker_col2#001@185-188");
  pthread_mutex_unlock(&mutex_06);
  sem_wait(&sem_ge_p1);
  pthread_mutex_lock(&mutex_07);
SEG_BEGIN("MU:worker_col2#002@189-192");
  busy_wait_seconds(C7);
SEG_END("MU:worker_col2#002@189-192");
  pthread_mutex_unlock(&mutex_07);
  pthread_mutex_lock(&mutex_08);
SEG_BEGIN("MU:worker_col2#003@193-198");
  busy_wait_seconds(C8);
SEG_END("MU:worker_col2#003@193-198");
  pthread_mutex_unlock(&mutex_08);
  sem_post(&sem_ge_p2);
  sem_post(&sem_ge_p2);
  sem_post(&sem_ge_p2);
  return NULL;
}

static void *worker_col3(void *arg) {
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_09);
SEG_BEGIN("MU:worker_col3#001@203-206");
  busy_wait_seconds(C9);
SEG_END("MU:worker_col3#001@203-206");
  pthread_mutex_unlock(&mutex_09);
  sem_wait(&sem_ge_p1);
  pthread_mutex_lock(&mutex_10);
SEG_BEGIN("MU:worker_col3#002@207-210");
  busy_wait_seconds(C10);
SEG_END("MU:worker_col3#002@207-210");
  pthread_mutex_unlock(&mutex_10);
  sem_wait(&sem_ge_p2);
  pthread_mutex_lock(&mutex_11);
SEG_BEGIN("MU:worker_col3#003@211-214");
  busy_wait_seconds(C11);
SEG_END("MU:worker_col3#003@211-214");
  pthread_mutex_unlock(&mutex_11);
  pthread_mutex_lock(&mutex_12);
SEG_BEGIN("MU:worker_col3#004@215-219");
  busy_wait_seconds(C12);
SEG_END("MU:worker_col3#004@215-219");
  pthread_mutex_unlock(&mutex_12);
  sem_post(&sem_ge_p3);
  sem_post(&sem_ge_p3);
  return NULL;
}

static void *worker_col4(void *arg) {
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_13);
SEG_BEGIN("MU:worker_col4#001@224-227");
  busy_wait_seconds(C13);
SEG_END("MU:worker_col4#001@224-227");
  pthread_mutex_unlock(&mutex_13);
  sem_wait(&sem_ge_p1);
  pthread_mutex_lock(&mutex_14);
SEG_BEGIN("MU:worker_col4#002@228-231");
  busy_wait_seconds(C14);
SEG_END("MU:worker_col4#002@228-231");
  pthread_mutex_unlock(&mutex_14);
  sem_wait(&sem_ge_p2);
  pthread_mutex_lock(&mutex_15);
SEG_BEGIN("MU:worker_col4#003@232-235");
  busy_wait_seconds(C15);
SEG_END("MU:worker_col4#003@232-235");
  pthread_mutex_unlock(&mutex_15);
  sem_wait(&sem_ge_p3);
  pthread_mutex_lock(&mutex_16);
SEG_BEGIN("MU:worker_col4#004@236-239");
  busy_wait_seconds(C16);
SEG_END("MU:worker_col4#004@236-239");
  pthread_mutex_unlock(&mutex_16);
  pthread_mutex_lock(&mutex_17);
SEG_BEGIN("MU:worker_col4#005@240-243");
  busy_wait_seconds(C17);
SEG_END("MU:worker_col4#005@240-243");
  pthread_mutex_unlock(&mutex_17);
  sem_post(&sem_ge_p4);
  return NULL;
}

static void *worker_col5(void *arg) {
  sem_wait(&sem_ge_p0);
  pthread_mutex_lock(&mutex_18);
SEG_BEGIN("MU:worker_col5#001@248-251");
  busy_wait_seconds(C18);
SEG_END("MU:worker_col5#001@248-251");
  pthread_mutex_unlock(&mutex_18);
  sem_wait(&sem_ge_p1);
  pthread_mutex_lock(&mutex_19);
SEG_BEGIN("MU:worker_col5#002@252-255");
  busy_wait_seconds(C19);
SEG_END("MU:worker_col5#002@252-255");
  pthread_mutex_unlock(&mutex_19);
  sem_wait(&sem_ge_p2);
  pthread_mutex_lock(&mutex_20);
SEG_BEGIN("MU:worker_col5#003@256-259");
  busy_wait_seconds(C20);
SEG_END("MU:worker_col5#003@256-259");
  pthread_mutex_unlock(&mutex_20);
  sem_wait(&sem_ge_p3);
  pthread_mutex_lock(&mutex_21);
SEG_BEGIN("MU:worker_col5#004@260-263");
  busy_wait_seconds(C21);
SEG_END("MU:worker_col5#004@260-263");
  pthread_mutex_unlock(&mutex_21);
  sem_wait(&sem_ge_p4);
  pthread_mutex_lock(&mutex_22);
SEG_BEGIN("MU:worker_col5#005@264-267");
  busy_wait_seconds(C22);
SEG_END("MU:worker_col5#005@264-267");
  pthread_mutex_unlock(&mutex_22);
  pthread_mutex_lock(&mutex_23);
SEG_BEGIN("MU:worker_col5#006@268-270");
  busy_wait_seconds(C23);
SEG_END("MU:worker_col5#006@268-270");
  pthread_mutex_unlock(&mutex_23);
  return NULL;
}

int main(void) {
  pthread_mutex_lock(&mutex_01);
SEG_BEGIN("MU:main#001@275-288");
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
SEG_END("MU:main#001@275-288");
  pthread_mutex_unlock(&mutex_01);
SEG_BEGIN("SEG:main#002@289-296");

  /* tail columns first: bad for FIFO equal-prio, good for ranked algos once prio injected */
  pthread_create(&t_col5, NULL, worker_col5, NULL);
  pthread_create(&t_col4, NULL, worker_col4, NULL);
  pthread_create(&t_col3, NULL, worker_col3, NULL);
  pthread_create(&t_col2, NULL, worker_col2, NULL);
  pthread_create(&t_col1, NULL, worker_col1, NULL);
  pthread_create(&t_col0, NULL, worker_col0, NULL);
SEG_END("SEG:main#002@289-296");
SEG_BEGIN("SEG:main#003@297-297");

SEG_END("SEG:main#003@297-297");
SEG_BEGIN("SEG:main#004@298-304");
  pthread_join(t_col0, NULL);
  pthread_join(t_col1, NULL);
  pthread_join(t_col2, NULL);
  pthread_join(t_col3, NULL);
  pthread_join(t_col4, NULL);
  pthread_join(t_col5, NULL);

SEG_END("SEG:main#004@298-304");
  pthread_mutex_lock(&mutex_02);
SEG_BEGIN("MU:main#005@305-307");
  busy_wait_seconds(C2);
SEG_END("MU:main#005@305-307");
  pthread_mutex_unlock(&mutex_02);
  return 0;
}
