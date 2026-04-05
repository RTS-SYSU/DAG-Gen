#define _GNU_SOURCE
#include "prio_runtime.h"
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * dag6: "Pipeline spine" — critical path crosses 4 threads (3 sem edges).
 *
 * Unlike dag4 (dense GE + pivot fan-out) and dag5 (one thread, 3 MU chain):
 *   stage0 ->(sem_01)-> stage1 ->(sem_12)-> stage2 ->(sem_23)-> stage3
 * Each stage is one heavy mutex+work block on its own thread.
 *
 * Six light fillers contend for 4 cores under CFS/FIFO while the pipeline must
 * stay hot; SCHED_FIFO + DAG priorities (cpf/heft/lpf/zhao2020, and t_level
 * with a_stage0 before filler_* lexicographically) favor the spine.
 *
 * pthread_create order: fillers first, then d,c,b,a so FIFO fills cores before
 * the head stage thread a_stage0 competes.
 */

#define C1    0.1   /* main#001 init */
#define C2    0.1   /* main#002 final */

/* Pipeline (critical path); keep high vs fillers */
#define C3    10.0  /* a_stage0 — first spine segment */
#define C4    10.0  /* b_stage1 */
#define C5    10.0  /* c_stage2 */
#define C6    10.0  /* d_stage3 */

/* Fillers */
#define C7    2.6   /* filler_01 */
#define C8    2.6   /* filler_02 */
#define C9    2.6   /* filler_03 */
#define C10   2.6   /* filler_04 */
#define C11   2.6   /* filler_05 */
#define C12   2.6   /* filler_06 */

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
static pthread_mutex_t mutex_10 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_11 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_12 = PTHREAD_MUTEX_INITIALIZER;

static sem_t sem_01;
static sem_t sem_12;
static sem_t sem_23;

static pthread_t t_f1, t_f2, t_f3, t_f4, t_f5, t_f6;
static pthread_t t_d, t_c, t_b, t_a;

static void *filler_01(void *arg) {
  l1_set_thread_prio_fifo(95);
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_03);
  return NULL;
}

static void *filler_02(void *arg) {
  l1_set_thread_prio_fifo(90);
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_04);
  return NULL;
}

static void *filler_03(void *arg) {
  l1_set_thread_prio_fifo(93);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_05);
  return NULL;
}

static void *filler_04(void *arg) {
  l1_set_thread_prio_fifo(94);
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

static void *filler_05(void *arg) {
  l1_set_thread_prio_fifo(92);
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_07);
  return NULL;
}

static void *filler_06(void *arg) {
  l1_set_thread_prio_fifo(91);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_08);
  return NULL;
}

static void *d_stage3(void *arg) {
  l1_set_thread_prio_fifo(97);
  sem_wait(&sem_23);
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_12);
  return NULL;
}

static void *c_stage2(void *arg) {
  l1_set_thread_prio_fifo(99);
  sem_wait(&sem_12);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_11);
  sem_post(&sem_23);
  return NULL;
}

static void *b_stage1(void *arg) {
  l1_set_thread_prio_fifo(98);
  sem_wait(&sem_01);
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_10);
  sem_post(&sem_12);
  return NULL;
}

static void *a_stage0(void *arg) {
  l1_set_thread_prio_fifo(96);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_09);
  sem_post(&sem_01);
  return NULL;
}

int main(void) {
  l1_set_thread_prio_fifo(89);
  pthread_mutex_lock(&mutex_01);
  init_matrices();
  if (sem_init(&sem_01, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_12, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_23, 0, 0) != 0)
    return 1;
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);

  pthread_create(&t_f1, NULL, filler_01, NULL);
  pthread_create(&t_f2, NULL, filler_02, NULL);
  pthread_create(&t_f3, NULL, filler_03, NULL);
  pthread_create(&t_f4, NULL, filler_04, NULL);
  pthread_create(&t_f5, NULL, filler_05, NULL);
  pthread_create(&t_f6, NULL, filler_06, NULL);
  pthread_create(&t_d, NULL, d_stage3, NULL);
  pthread_create(&t_c, NULL, c_stage2, NULL);
  pthread_create(&t_b, NULL, b_stage1, NULL);
  pthread_create(&t_a, NULL, a_stage0, NULL);

  l1_set_thread_prio_fifo(88);
  pthread_join(t_f1, NULL);
  pthread_join(t_f2, NULL);
  pthread_join(t_f3, NULL);
  pthread_join(t_f4, NULL);
  pthread_join(t_f5, NULL);
  pthread_join(t_f6, NULL);
  pthread_join(t_d, NULL);
  pthread_join(t_c, NULL);
  pthread_join(t_b, NULL);
  pthread_join(t_a, NULL);

  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
  return 0;
}
