#define _GNU_SOURCE
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * dag7: 4-core experiment DAG with few sem edges and paired create/join.
 *
 * Constraints followed from the experiment docs:
 *   - keep the graph simple: only 2 sem_post/sem_wait pairs;
 *   - keep create/join paired: 6 creates + 6 joins;
 *   - build at least 2 competition windows, each with about 5 runnable tasks
 *     under the 4-core setting.
 *
 * Topology:
 *   main#001(C1)  --create 6 workers-->  main#002(C2) --post(s2)-->
 *        |                                   |                     |
 *        |                                   +---------------------+
 *        |                                                       join all
 *        +--> a_head#001(C4) --post(s1)--------------------------->|
 *        +--> b_tail#001(wait s1, C5) ---------------------------->|
 *        +--> filler_c#001(C6) ----------------------------------->|
 *        +--> filler_d#001(C7) ----------------------------------->|
 *        +--> filler_e#001(C8) ----------------------------------->|
 *        +--> late_f#001(wait s2, C9) ---------------------------->|
 *   main#003(C3)
 *
 * Competition windows on 4 cores:
 *   1. after main#001: main#002 + a_head + filler_c + filler_d + filler_e
 *   2. after s1 and s2 are released: b_tail + late_f + filler_c + filler_d +
 *      filler_e
 *
 * Design intent:
 *   - a_head -> b_tail is the unique critical path and directly gates the
 *     final join, so DAG-aware policies should favor it.
 *   - fillers are long enough to maintain contention, but lighter than the
 *     critical segments so rank/WCET based algorithms have a reason to choose
 *     the critical chain.
 *   - main stays light; it only creates, does one light transition block, then
 *     joins. That avoids the "main trigger path is starved" failure mode.
 */

#define C1   0.3   /* main#001 */
#define C2   0.6   /* main#002 */
#define C3   0.1   /* main#003 */
#define C4   8.4   /* a_head */
#define C5   9.2   /* b_tail */
#define C6   3.4   /* filler_c */
#define C7   3.4   /* filler_d */
#define C8   3.4   /* filler_e */
#define C9   4.0   /* late_f */

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

static pthread_mutex_t mutex_01 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_02 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_03 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_04 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_05 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_06 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_07 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_08 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_09 = PTHREAD_MUTEX_INITIALIZER;

static sem_t sem_01;
static sem_t sem_02;

static pthread_t t_a_head;
static pthread_t t_b_tail;
static pthread_t t_filler_c;
static pthread_t t_filler_d;
static pthread_t t_filler_e;
static pthread_t t_late_f;

static void *a_head(void *arg) {
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  sem_post(&sem_01);
  return NULL;
}

static void *b_tail(void *arg) {
  sem_wait(&sem_01);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  return NULL;
}

static void *filler_c(void *arg) {
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

static void *filler_d(void *arg) {
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);
  return NULL;
}

static void *filler_e(void *arg) {
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_08);
  return NULL;
}

static void *late_f(void *arg) {
  sem_wait(&sem_02);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_09);
  return NULL;
}

int main(void) {
    struct timespec ts_main_begin, ts_main_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);
  pthread_mutex_lock(&mutex_01);
  init_matrices();
  if (sem_init(&sem_01, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_02, 0, 0) != 0)
    return 1;
  busy_wait_seconds(C1);
  pthread_create(&t_filler_c, NULL, filler_c, NULL);
  pthread_create(&t_filler_d, NULL, filler_d, NULL);
  pthread_create(&t_filler_e, NULL, filler_e, NULL);
  pthread_create(&t_late_f, NULL, late_f, NULL);
  pthread_create(&t_b_tail, NULL, b_tail, NULL);
  pthread_create(&t_a_head, NULL, a_head, NULL);
  pthread_mutex_unlock(&mutex_01);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  sem_post(&sem_02);
  pthread_mutex_unlock(&mutex_02);
  pthread_mutex_lock(&mutex_03);
  pthread_join(t_filler_c, NULL);
  pthread_join(t_filler_d, NULL);
  pthread_join(t_filler_e, NULL);
  pthread_join(t_late_f, NULL);
  pthread_join(t_b_tail, NULL);
  pthread_join(t_a_head, NULL);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);
    {
        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)
            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;
        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\n", main_s);
    }
  return 0;
}
