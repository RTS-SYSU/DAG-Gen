#define _GNU_SOURCE
#include "segtrace.h"
#include <pthread.h>

/*
 * dag8: "Cascade spine" -- a 5-stage critical chain released by thread creation.
 *
 * Topology:
 *
 *   main#001(C1) -> fork filler_01..06 + a_stage0 -> join(a_stage0) -> join fillers -> main#002(C2)
 *                                  |
 *                                  +-> a_stage0#001(C3) -> create z_late_01..03 + b_stage1#001(C4)
 *                                                         -> join(b_stage1) -> join(z_late_01..03)
 *                                                              |
 *                                                              +-> b_stage1#001(C4) -> create z_late_04..05 + c_stage2#001(C5)
 *                                                                                     -> join(c_stage2) -> join(z_late_04..05)
 *                                                                                          |
 *                                                                                          +-> c_stage2#001(C5) -> create z_late_06..07 + d_stage3#001(C6)
 *                                                                                                                 -> join(d_stage3) -> join(z_late_06..07)
 *                                                                                                                      |
 *                                                                                                                      +-> d_stage3#001(C6) -> create e_stage4#001(C7)
 *                                                                                                                                             -> join(e_stage4)
 *
 * Design goals from the experiment notes:
 * - keep main light and off the critical path after the initial fork
 * - keep each critical worker to a single MU block to avoid priority drops
 * - create fillers before the next stage so same-priority FIFO is biased away
 *   from the spine, while DAG-based priorities can still preempt correctly
 * - maintain multiple wide competition windows for both 2-core and 4-core runs
 */

/* ---- Weight constants -------------------------------------------------- */
#define C1   0.1  /* main#001 init */
#define C2   0.1  /* main#002 post-create bridge */

/* Critical spine */
#define C3   9.2  /* a_stage0 */
#define C4   8.8  /* b_stage1 */
#define C5   8.4  /* c_stage2 */
#define C6   8.0  /* d_stage3 */
#define C7   7.6  /* e_stage4 */

/* Early fillers created by main */
#define C8   3.1  /* filler_01 */
#define C9   3.1  /* filler_02 */
#define C10  3.1  /* filler_03 */
#define C11  3.1  /* filler_04 */
#define C12  3.1  /* filler_05 */
#define C13  3.1  /* filler_06 */

/* Late fillers released by the spine */
#define C14  3.8  /* z_late_01 */
#define C15  3.8  /* z_late_02 */
#define C16  3.8  /* z_late_03 */
#define C17  3.5  /* z_late_04 */
#define C18  3.5  /* z_late_05 */
#define C19  2.8  /* z_late_06 */
#define C20  2.8  /* z_late_07 */

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

/* ---- Mutexes (20 total, one per MU block) ------------------------------ */
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

/* ---- Thread handles ---------------------------------------------------- */
static pthread_t t_stage_0;
static pthread_t t_stage_1;
static pthread_t t_stage_2;
static pthread_t t_stage_3;
static pthread_t t_stage_4;
static pthread_t t_filler_01;
static pthread_t t_filler_02;
static pthread_t t_filler_03;
static pthread_t t_filler_04;
static pthread_t t_filler_05;
static pthread_t t_filler_06;
static pthread_t t_late_01;
static pthread_t t_late_02;
static pthread_t t_late_03;
static pthread_t t_late_04;
static pthread_t t_late_05;
static pthread_t t_late_06;
static pthread_t t_late_07;

/* ---- Worker declarations ----------------------------------------------- */
static void *a_stage0(void *arg);
static void *b_stage1(void *arg);
static void *c_stage2(void *arg);
static void *d_stage3(void *arg);
static void *e_stage4(void *arg);
static void *filler_01(void *arg);
static void *filler_02(void *arg);
static void *filler_03(void *arg);
static void *filler_04(void *arg);
static void *filler_05(void *arg);
static void *filler_06(void *arg);
static void *z_late_01(void *arg);
static void *z_late_02(void *arg);
static void *z_late_03(void *arg);
static void *z_late_04(void *arg);
static void *z_late_05(void *arg);
static void *z_late_06(void *arg);
static void *z_late_07(void *arg);

/* ---- Spine workers ----------------------------------------------------- */
static void *a_stage0(void *arg)
{
  pthread_mutex_lock(&mutex_03);
SEG_BEGIN("MU:a_stage0#001@167-173");
  busy_wait_seconds(C3);
SEG_END("MU:a_stage0#001@167-173");
  pthread_mutex_unlock(&mutex_03);
  pthread_create(&t_late_01, NULL, z_late_01, NULL);
  pthread_create(&t_late_02, NULL, z_late_02, NULL);
  pthread_create(&t_late_03, NULL, z_late_03, NULL);
  pthread_create(&t_stage_1, NULL, b_stage1, NULL);
  return NULL;
}

static void *b_stage1(void *arg)
{
  pthread_mutex_lock(&mutex_04);
SEG_BEGIN("MU:b_stage1#001@179-184");
  busy_wait_seconds(C4);
SEG_END("MU:b_stage1#001@179-184");
  pthread_mutex_unlock(&mutex_04);
  pthread_create(&t_late_04, NULL, z_late_04, NULL);
  pthread_create(&t_late_05, NULL, z_late_05, NULL);
  pthread_create(&t_stage_2, NULL, c_stage2, NULL);
  return NULL;
}

static void *c_stage2(void *arg)
{
  pthread_mutex_lock(&mutex_05);
SEG_BEGIN("MU:c_stage2#001@190-195");
  busy_wait_seconds(C5);
SEG_END("MU:c_stage2#001@190-195");
  pthread_mutex_unlock(&mutex_05);
  pthread_create(&t_late_06, NULL, z_late_06, NULL);
  pthread_create(&t_late_07, NULL, z_late_07, NULL);
  pthread_create(&t_stage_3, NULL, d_stage3, NULL);
  return NULL;
}

static void *d_stage3(void *arg)
{
  pthread_mutex_lock(&mutex_06);
SEG_BEGIN("MU:d_stage3#001@201-204");
  busy_wait_seconds(C6);
SEG_END("MU:d_stage3#001@201-204");
  pthread_mutex_unlock(&mutex_06);
  pthread_create(&t_stage_4, NULL, e_stage4, NULL);
  return NULL;
}

static void *e_stage4(void *arg)
{
  pthread_mutex_lock(&mutex_07);
SEG_BEGIN("MU:e_stage4#001@210-212");
  busy_wait_seconds(C7);
SEG_END("MU:e_stage4#001@210-212");
  pthread_mutex_unlock(&mutex_07);
  return NULL;
}

/* ---- Early fillers ----------------------------------------------------- */
static void *filler_01(void *arg)
{
  pthread_mutex_lock(&mutex_08);
SEG_BEGIN("MU:filler_01#001@219-221");
  busy_wait_seconds(C8);
SEG_END("MU:filler_01#001@219-221");
  pthread_mutex_unlock(&mutex_08);
  return NULL;
}

static void *filler_02(void *arg)
{
  pthread_mutex_lock(&mutex_09);
SEG_BEGIN("MU:filler_02#001@227-229");
  busy_wait_seconds(C9);
SEG_END("MU:filler_02#001@227-229");
  pthread_mutex_unlock(&mutex_09);
  return NULL;
}

static void *filler_03(void *arg)
{
  pthread_mutex_lock(&mutex_10);
SEG_BEGIN("MU:filler_03#001@235-237");
  busy_wait_seconds(C10);
SEG_END("MU:filler_03#001@235-237");
  pthread_mutex_unlock(&mutex_10);
  return NULL;
}

static void *filler_04(void *arg)
{
  pthread_mutex_lock(&mutex_11);
SEG_BEGIN("MU:filler_04#001@243-245");
  busy_wait_seconds(C11);
SEG_END("MU:filler_04#001@243-245");
  pthread_mutex_unlock(&mutex_11);
  return NULL;
}

static void *filler_05(void *arg)
{
  pthread_mutex_lock(&mutex_12);
SEG_BEGIN("MU:filler_05#001@251-253");
  busy_wait_seconds(C12);
SEG_END("MU:filler_05#001@251-253");
  pthread_mutex_unlock(&mutex_12);
  return NULL;
}

static void *filler_06(void *arg)
{
  pthread_mutex_lock(&mutex_13);
SEG_BEGIN("MU:filler_06#001@259-261");
  busy_wait_seconds(C13);
SEG_END("MU:filler_06#001@259-261");
  pthread_mutex_unlock(&mutex_13);
  return NULL;
}

/* ---- Late fillers ------------------------------------------------------ */
static void *z_late_01(void *arg)
{
  pthread_mutex_lock(&mutex_14);
SEG_BEGIN("MU:z_late_01#001@268-270");
  busy_wait_seconds(C14);
SEG_END("MU:z_late_01#001@268-270");
  pthread_mutex_unlock(&mutex_14);
  return NULL;
}

static void *z_late_02(void *arg)
{
  pthread_mutex_lock(&mutex_15);
SEG_BEGIN("MU:z_late_02#001@276-278");
  busy_wait_seconds(C15);
SEG_END("MU:z_late_02#001@276-278");
  pthread_mutex_unlock(&mutex_15);
  return NULL;
}

static void *z_late_03(void *arg)
{
  pthread_mutex_lock(&mutex_16);
SEG_BEGIN("MU:z_late_03#001@284-286");
  busy_wait_seconds(C16);
SEG_END("MU:z_late_03#001@284-286");
  pthread_mutex_unlock(&mutex_16);
  return NULL;
}

static void *z_late_04(void *arg)
{
  pthread_mutex_lock(&mutex_17);
SEG_BEGIN("MU:z_late_04#001@292-294");
  busy_wait_seconds(C17);
SEG_END("MU:z_late_04#001@292-294");
  pthread_mutex_unlock(&mutex_17);
  return NULL;
}

static void *z_late_05(void *arg)
{
  pthread_mutex_lock(&mutex_18);
SEG_BEGIN("MU:z_late_05#001@300-302");
  busy_wait_seconds(C18);
SEG_END("MU:z_late_05#001@300-302");
  pthread_mutex_unlock(&mutex_18);
  return NULL;
}

static void *z_late_06(void *arg)
{
  pthread_mutex_lock(&mutex_19);
SEG_BEGIN("MU:z_late_06#001@308-310");
  busy_wait_seconds(C19);
SEG_END("MU:z_late_06#001@308-310");
  pthread_mutex_unlock(&mutex_19);
  return NULL;
}

static void *z_late_07(void *arg)
{
  pthread_mutex_lock(&mutex_20);
SEG_BEGIN("MU:z_late_07#001@316-318");
  busy_wait_seconds(C20);
SEG_END("MU:z_late_07#001@316-318");
  pthread_mutex_unlock(&mutex_20);
  return NULL;
}

/* ---- main -------------------------------------------------------------- */
int main(void)
{
  pthread_mutex_lock(&mutex_01);
SEG_BEGIN("MU:main#001@325-335");
  init_matrices();
  busy_wait_seconds(C1);
SEG_END("MU:main#001@325-335");
  pthread_mutex_unlock(&mutex_01);
  pthread_create(&t_filler_01, NULL, filler_01, NULL);
  pthread_create(&t_filler_02, NULL, filler_02, NULL);
  pthread_create(&t_filler_03, NULL, filler_03, NULL);
  pthread_create(&t_filler_04, NULL, filler_04, NULL);
  pthread_create(&t_filler_05, NULL, filler_05, NULL);
  pthread_create(&t_filler_06, NULL, filler_06, NULL);
  pthread_create(&t_stage_0, NULL, a_stage0, NULL);
  pthread_join(t_stage_0, NULL);
  pthread_join(t_stage_1, NULL);
  pthread_join(t_stage_2, NULL);
  pthread_join(t_stage_3, NULL);
  pthread_join(t_stage_4, NULL);
  pthread_join(t_late_01, NULL);
  pthread_join(t_late_02, NULL);
  pthread_join(t_late_03, NULL);
  pthread_join(t_late_04, NULL);
  pthread_join(t_late_05, NULL);
  pthread_join(t_late_06, NULL);
  pthread_join(t_late_07, NULL);
  pthread_join(t_filler_01, NULL);
  pthread_join(t_filler_02, NULL);
  pthread_join(t_filler_03, NULL);
  pthread_join(t_filler_04, NULL);
  pthread_join(t_filler_05, NULL);
  pthread_join(t_filler_06, NULL);
  pthread_mutex_lock(&mutex_02);
SEG_BEGIN("MU:main#002@336-356");
  busy_wait_seconds(C2);
SEG_END("MU:main#002@336-356");
  pthread_mutex_unlock(&mutex_02);
  return 0;
}
