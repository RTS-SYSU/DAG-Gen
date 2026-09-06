#define _GNU_SOURCE
#include "prio_runtime.h"
#include <pthread.h>
#include <semaphore.h>

/*
 * dag9: "Double-gate hourglass" -- a 5-stage critical chain with
 * three contention windows.
 *
 * Topology:
 *
 *   main#001(C1)
 *     -> create filler_early_01..04
 *     -> create filler_mid_01..04(wait on sem_mid_*)
 *     -> create b_left(wait sem_left), c_right(wait sem_right), d_merge(wait merge)
 *     -> create a_gate
 *
 *   a_gate#001(C3)
 *     -> post sem_mid_01..04
 *     -> post sem_left
 *     -> post sem_right
 *
 *   b_left#001(C4)  -> post sem_merge_left
 *   c_right#001(C5) -> post sem_merge_right
 *
 *   d_merge#001(C6)
 *     wait sem_merge_left + sem_merge_right
 *     -> create filler_late_01..04
 *     -> create e_tail
 *
 *   e_tail#001(C7)
 *   main#002(C2) after join all
 *
 * Design intent:
 * - keep the critical chain concentrated in single-MU workers
 * - keep main light so it only gates fork/join and avoids trigger starvation
 * - release mid and late fillers from critical nodes to create two follow-up
 *   contention windows for both 2-core and 4-core runs
 * - bias same-priority FIFO away from the chain through create order, while
 *   allowing DAG-aware priorities to preempt toward the chain
 */

/* ---- Weight constants -------------------------------------------------- */
#define C1   0.1  /* main#001 init */
#define C2   0.1  /* main#002 final */

/* Critical chain */
#define C3   9.6  /* a_gate */
#define C4   8.8  /* b_left */
#define C5   8.4  /* c_right */
#define C6   9.2  /* d_merge */
#define C7   9.8  /* e_tail */

/* Early fillers */
#define C8   3.1  /* filler_early_01 */
#define C9   3.1  /* filler_early_02 */
#define C10  3.1  /* filler_early_03 */
#define C11  3.1  /* filler_early_04 */

/* Mid fillers */
#define C12  4.1  /* filler_mid_01 */
#define C13  4.0  /* filler_mid_02 */
#define C14  3.9  /* filler_mid_03 */
#define C15  3.8  /* filler_mid_04 */

/* Late fillers */
#define C16  4.3  /* filler_late_01 */
#define C17  4.2  /* filler_late_02 */
#define C18  4.0  /* filler_late_03 */
#define C19  3.9  /* filler_late_04 */

/* ---- Busy-wait infrastructure ------------------------------------------ */
#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];
static volatile double g_busy_sink = 0.0;

static void init_matrices(void)
{
  for (int i = 0; i < MAT_N; i++)
    for (int j = 0; j < MAT_N; j++) {
      mat_a[i][j] = (double)(i + j) * 0.001;
      mat_b[i][j] = (double)(i - j) * 0.001;
    }
}

static void busy_wait_seconds(double seconds)
{
  int units = (int)(seconds * WORK_SCALE + 0.5);

  if (units < 1)
    units = 1;

  for (int u = 0; u < units; u++) {
    for (int i = 0; i < MAT_N; i++) {
      for (int j = 0; j < MAT_N; j++) {
        double s = 0.0;

        for (int k = 0; k < MAT_N; k++)
          s += mat_a[i][k] * mat_b[k][j];

        mat_c[i][j] = s;
      }
    }
  }

  g_busy_sink += mat_c[0][0];
}

/* ---- Mutexes (19 total, one per MU block) ------------------------------ */
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

/* ---- Semaphores -------------------------------------------------------- */
static sem_t sem_left;
static sem_t sem_right;
static sem_t sem_mid_01;
static sem_t sem_mid_02;
static sem_t sem_mid_03;
static sem_t sem_mid_04;
static sem_t sem_merge_left;
static sem_t sem_merge_right;

/* ---- Thread handles ---------------------------------------------------- */
static pthread_t t_a_gate;
static pthread_t t_b_left;
static pthread_t t_c_right;
static pthread_t t_d_merge;
static pthread_t t_e_tail;
static pthread_t t_filler_early_01;
static pthread_t t_filler_early_02;
static pthread_t t_filler_early_03;
static pthread_t t_filler_early_04;
static pthread_t t_filler_mid_01;
static pthread_t t_filler_mid_02;
static pthread_t t_filler_mid_03;
static pthread_t t_filler_mid_04;
static pthread_t t_filler_late_01;
static pthread_t t_filler_late_02;
static pthread_t t_filler_late_03;
static pthread_t t_filler_late_04;

/* ---- Worker declarations ----------------------------------------------- */
static void *a_gate(void *arg);
static void *b_left(void *arg);
static void *c_right(void *arg);
static void *d_merge(void *arg);
static void *e_tail(void *arg);
static void *filler_early_01(void *arg);
static void *filler_early_02(void *arg);
static void *filler_early_03(void *arg);
static void *filler_early_04(void *arg);
static void *filler_mid_01(void *arg);
static void *filler_mid_02(void *arg);
static void *filler_mid_03(void *arg);
static void *filler_mid_04(void *arg);
static void *filler_late_01(void *arg);
static void *filler_late_02(void *arg);
static void *filler_late_03(void *arg);
static void *filler_late_04(void *arg);

/* ---- Critical chain ---------------------------------------------------- */
static void *a_gate(void *arg)
{
  l1_set_thread_prio_fifo(98);
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  sem_post(&sem_mid_01);
  sem_post(&sem_mid_02);
  sem_post(&sem_mid_03);
  sem_post(&sem_mid_04);
  sem_post(&sem_left);
  sem_post(&sem_right);
  return NULL;
}

static void *b_left(void *arg)
{
  l1_set_thread_prio_fifo(97);
  sem_wait(&sem_left);
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  sem_post(&sem_merge_left);
  return NULL;
}

static void *c_right(void *arg)
{
  l1_set_thread_prio_fifo(93);
  sem_wait(&sem_right);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  sem_post(&sem_merge_right);
  return NULL;
}

static void *d_merge(void *arg)
{
  l1_set_thread_prio_fifo(96);
  sem_wait(&sem_merge_left);
  sem_wait(&sem_merge_right);
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);
  pthread_create(&t_filler_late_01, NULL, filler_late_01, NULL);
  pthread_create(&t_filler_late_02, NULL, filler_late_02, NULL);
  pthread_create(&t_filler_late_03, NULL, filler_late_03, NULL);
  pthread_create(&t_filler_late_04, NULL, filler_late_04, NULL);
  pthread_create(&t_e_tail, NULL, e_tail, NULL);
  return NULL;
}

static void *e_tail(void *arg)
{
  l1_set_thread_prio_fifo(95);
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);
  return NULL;
}

/* ---- Early fillers ----------------------------------------------------- */
static void *filler_early_01(void *arg)
{
  l1_set_thread_prio_fifo(82);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_08);
  return NULL;
}

static void *filler_early_02(void *arg)
{
  l1_set_thread_prio_fifo(84);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_09);
  return NULL;
}

static void *filler_early_03(void *arg)
{
  l1_set_thread_prio_fifo(81);
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_10);
  return NULL;
}

static void *filler_early_04(void *arg)
{
  l1_set_thread_prio_fifo(83);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_11);
  return NULL;
}

/* ---- Mid fillers ------------------------------------------------------- */
static void *filler_mid_01(void *arg)
{
  l1_set_thread_prio_fifo(88);
  sem_wait(&sem_mid_01);
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_12);
  return NULL;
}

static void *filler_mid_02(void *arg)
{
  l1_set_thread_prio_fifo(86);
  sem_wait(&sem_mid_02);
  pthread_mutex_lock(&mutex_13);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_13);
  return NULL;
}

static void *filler_mid_03(void *arg)
{
  l1_set_thread_prio_fifo(92);
  sem_wait(&sem_mid_03);
  pthread_mutex_lock(&mutex_14);
  busy_wait_seconds(C14);
  pthread_mutex_unlock(&mutex_14);
  return NULL;
}

static void *filler_mid_04(void *arg)
{
  l1_set_thread_prio_fifo(91);
  sem_wait(&sem_mid_04);
  pthread_mutex_lock(&mutex_15);
  busy_wait_seconds(C15);
  pthread_mutex_unlock(&mutex_15);
  return NULL;
}

/* ---- Late fillers ------------------------------------------------------ */
static void *filler_late_01(void *arg)
{
  l1_set_thread_prio_fifo(85);
  pthread_mutex_lock(&mutex_16);
  busy_wait_seconds(C16);
  pthread_mutex_unlock(&mutex_16);
  return NULL;
}

static void *filler_late_02(void *arg)
{
  l1_set_thread_prio_fifo(90);
  pthread_mutex_lock(&mutex_17);
  busy_wait_seconds(C17);
  pthread_mutex_unlock(&mutex_17);
  return NULL;
}

static void *filler_late_03(void *arg)
{
  l1_set_thread_prio_fifo(89);
  pthread_mutex_lock(&mutex_18);
  busy_wait_seconds(C18);
  pthread_mutex_unlock(&mutex_18);
  return NULL;
}

static void *filler_late_04(void *arg)
{
  l1_set_thread_prio_fifo(87);
  pthread_mutex_lock(&mutex_19);
  busy_wait_seconds(C19);
  pthread_mutex_unlock(&mutex_19);
  return NULL;
}

/* ---- main -------------------------------------------------------------- */
int main(void)
{
  l1_set_thread_prio_fifo(99);
  pthread_mutex_lock(&mutex_01);
  init_matrices();
  sem_init(&sem_left, 0, 0);
  sem_init(&sem_right, 0, 0);
  sem_init(&sem_mid_01, 0, 0);
  sem_init(&sem_mid_02, 0, 0);
  sem_init(&sem_mid_03, 0, 0);
  sem_init(&sem_mid_04, 0, 0);
  sem_init(&sem_merge_left, 0, 0);
  sem_init(&sem_merge_right, 0, 0);
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);
  pthread_create(&t_filler_early_01, NULL, filler_early_01, NULL);
  pthread_create(&t_filler_early_02, NULL, filler_early_02, NULL);
  pthread_create(&t_filler_early_03, NULL, filler_early_03, NULL);
  pthread_create(&t_filler_early_04, NULL, filler_early_04, NULL);
  pthread_create(&t_filler_mid_01, NULL, filler_mid_01, NULL);
  pthread_create(&t_filler_mid_02, NULL, filler_mid_02, NULL);
  pthread_create(&t_filler_mid_03, NULL, filler_mid_03, NULL);
  pthread_create(&t_filler_mid_04, NULL, filler_mid_04, NULL);
  pthread_create(&t_b_left, NULL, b_left, NULL);
  pthread_create(&t_c_right, NULL, c_right, NULL);
  pthread_create(&t_d_merge, NULL, d_merge, NULL);
  pthread_create(&t_a_gate, NULL, a_gate, NULL);
  l1_set_thread_prio_fifo(94);
  pthread_join(t_a_gate, NULL);
  pthread_join(t_b_left, NULL);
  pthread_join(t_c_right, NULL);
  pthread_join(t_d_merge, NULL);
  pthread_join(t_e_tail, NULL);
  pthread_join(t_filler_late_01, NULL);
  pthread_join(t_filler_late_02, NULL);
  pthread_join(t_filler_late_03, NULL);
  pthread_join(t_filler_late_04, NULL);
  pthread_join(t_filler_mid_01, NULL);
  pthread_join(t_filler_mid_02, NULL);
  pthread_join(t_filler_mid_03, NULL);
  pthread_join(t_filler_mid_04, NULL);
  pthread_join(t_filler_early_01, NULL);
  pthread_join(t_filler_early_02, NULL);
  pthread_join(t_filler_early_03, NULL);
  pthread_join(t_filler_early_04, NULL);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
  return 0;
}
