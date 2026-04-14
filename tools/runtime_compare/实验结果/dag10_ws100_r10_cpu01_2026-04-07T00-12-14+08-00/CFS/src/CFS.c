#define _GNU_SOURCE
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * dag10: small sem-window DAG for both 2-core and 4-core experiments.
 *
 * Topology:
 *   main#001(C1) --create 10 workers--> main#002(C2) --post(s2)--> late_f
 *        |                                  |
 *        |                                  +--------------------------+
 *        |                                                             |
 *        +--> filler_01#001(C8) -------------------------------------->|
 *        +--> filler_02#001(C9) -------------------------------------->|
 *        +--> filler_03#001(C10) ------------------------------------->|
 *        +--> filler_04#001(C11) ------------------------------------->|
 *        +--> filler_05#001(C12) ------------------------------------->|
 *        +--> filler_06#001(C13) ------------------------------------->|
 *        +--> late_f#001(wait s2, C7) -------------------------------->|
 *        +--> c_tail#001(wait s3, C6) -------------------------------->|
 *        +--> b_mid#001(wait s1, C5) --------------------------------->|
 *        +--> a_head#001(C4) --post(s1)--> b_mid --post(s3)--> c_tail |
 *                                                                  join all
 *   main#003(C3)
 *
 * Design intent:
 *   - a_head -> b_mid -> c_tail is the unique critical chain and directly
 *     gates the final join.
 *   - six equal fillers and one late branch keep both c2 and c4 contention
 *     high enough for scheduler differences to show up.
 *   - FIFO is biased toward fillers by creation order; DAG-aware policies can
 *     still pull the critical chain forward with higher priorities.
 */

#define C1   0.2
#define C2   0.8
#define C3   0.1
#define C4   7.8
#define C5   8.6
#define C6   9.4
#define C7   4.8
#define C8   4.6
#define C9   4.6
#define C10  4.6
#define C11  4.6
#define C12  4.6
#define C13  4.6

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

  if (units < 1)
    units = 1;

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
static pthread_mutex_t mutex_10 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_11 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_12 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_13 = PTHREAD_MUTEX_INITIALIZER;

static sem_t sem_01;
static sem_t sem_02;
static sem_t sem_03;

static pthread_t t_filler_01;
static pthread_t t_filler_02;
static pthread_t t_filler_03;
static pthread_t t_filler_04;
static pthread_t t_filler_05;
static pthread_t t_filler_06;
static pthread_t t_late_f;
static pthread_t t_c_tail;
static pthread_t t_b_mid;
static pthread_t t_a_head;

static void *a_head(void *arg) {
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  sem_post(&sem_01);
  return NULL;
}

static void *b_mid(void *arg) {
  sem_wait(&sem_01);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  sem_post(&sem_03);
  return NULL;
}

static void *c_tail(void *arg) {
  sem_wait(&sem_03);
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

static void *late_f(void *arg) {
  sem_wait(&sem_02);
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);
  return NULL;
}

static void *filler_01(void *arg) {
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_08);
  return NULL;
}

static void *filler_02(void *arg) {
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_09);
  return NULL;
}

static void *filler_03(void *arg) {
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_10);
  return NULL;
}

static void *filler_04(void *arg) {
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_11);
  return NULL;
}

static void *filler_05(void *arg) {
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_12);
  return NULL;
}

static void *filler_06(void *arg) {
  pthread_mutex_lock(&mutex_13);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_13);
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
  if (sem_init(&sem_03, 0, 0) != 0)
    return 1;
  busy_wait_seconds(C1);
  pthread_create(&t_filler_01, NULL, filler_01, NULL);
  pthread_create(&t_filler_02, NULL, filler_02, NULL);
  pthread_create(&t_filler_03, NULL, filler_03, NULL);
  pthread_create(&t_filler_04, NULL, filler_04, NULL);
  pthread_create(&t_filler_05, NULL, filler_05, NULL);
  pthread_create(&t_filler_06, NULL, filler_06, NULL);
  pthread_create(&t_late_f, NULL, late_f, NULL);
  pthread_create(&t_c_tail, NULL, c_tail, NULL);
  pthread_create(&t_b_mid, NULL, b_mid, NULL);
  pthread_create(&t_a_head, NULL, a_head, NULL);
  pthread_mutex_unlock(&mutex_01);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  sem_post(&sem_02);
  pthread_mutex_unlock(&mutex_02);
  pthread_mutex_lock(&mutex_03);
  pthread_join(t_filler_01, NULL);
  pthread_join(t_filler_02, NULL);
  pthread_join(t_filler_03, NULL);
  pthread_join(t_filler_04, NULL);
  pthread_join(t_filler_05, NULL);
  pthread_join(t_filler_06, NULL);
  pthread_join(t_late_f, NULL);
  pthread_join(t_c_tail, NULL);
  pthread_join(t_b_mid, NULL);
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
