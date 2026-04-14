#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * dag3: Laplace(phi=6) DAG — 4-core scheduling benchmark.
 *
 * 36 Laplace nodes + 2 main bookends = 38 MU blocks.
 * 6 worker threads (lane1..lane6), 30 semaphores.
 *
 * Diamond topology (11 layers, max width 6 at L6):
 *
 *   L1:           1
 *   L2:         1   2
 *   L3:       1   2   3
 *   L4:     1   2   3   4
 *   L5:   1   2   3   4   5
 *   L6: 1   2   3   4   5   6       <-- peak parallelism
 *   L7:   1   2   3   4   5
 *   L8:     1   2   3   4
 *   L9:       1   2   3
 *   L10:        1   2
 *   L11:          1
 *
 * Thread assignment (vertical lanes through the diamond):
 *   lane1: L1-L11, positions 1  (11 nodes, critical path)
 *   lane2: L2-L10, positions 2  (9 nodes)
 *   lane3: L3-L9,  positions 3  (7 nodes)
 *   lane4: L4-L8,  positions 4  (5 nodes)
 *   lane5: L5-L7,  positions 5  (3 nodes)
 *   lane6: L6,     position  6  (1 node)
 *
 * Expansion (L1->L6): node(k+1,j) depends on node(k,j) [same lane]
 *                      + node(k,j-1) [left-neighbor lane, via sem]
 * Contraction (L6->L11): node(k+1,j) depends on node(k,j) [same lane]
 *                         + node(k,j+1) [right-neighbor lane, via sem]
 */

/* ---- Weight constants -------------------------------------------------- */
#define C1   0.1    /* main#001  init          */
#define C2   1.4    /* lane1 L1                */
#define C3   1.4    /* lane1 L2                */
#define C4   1.2    /* lane1 L3                */
#define C5   1.0    /* lane1 L4                */
#define C6   0.8    /* lane1 L5                */
#define C7   0.8    /* lane1 L6                */
#define C8   0.7    /* lane1 L7                */
#define C9   0.7    /* lane1 L8                */
#define C10  0.8    /* lane1 L9                */
#define C11  0.9    /* lane1 L10               */
#define C12  1.0    /* lane1 L11               */
#define C13  0.4    /* lane2 L2                */
#define C14  1.0    /* lane2 L3                */
#define C15  0.5    /* lane2 L4                */
#define C16  1.5    /* lane2 L5                */
#define C17  2.0    /* lane2 L6                */
#define C18  2.8    /* lane2 L7                */
#define C19  3.8    /* lane2 L8                */
#define C20  3.8    /* lane2 L9                */
#define C21  2.9    /* lane2 L10               */
#define C22  0.5    /* lane3 L3                */
#define C23  1.2    /* lane3 L4                */
#define C24  1.2    /* lane3 L5                */
#define C25  2.5    /* lane3 L6                */
#define C26  2.5    /* lane3 L7                */
#define C27  3.2    /* lane3 L8                */
#define C28  3.0    /* lane3 L9                */
#define C29  1.0    /* lane4 L4                */
#define C30  1.4    /* lane4 L5                */
#define C31  2.6    /* lane4 L6                */
#define C32  3.1    /* lane4 L7                */
#define C33  3.6    /* lane4 L8                */
#define C34  1.2    /* lane5 L5                */
#define C35  2.8    /* lane5 L6                */
#define C36  3.8    /* lane5 L7                */
#define C37  4.4    /* lane6 L6                */
#define C38  0.1    /* main#002  final         */

/* ---- Busy-wait infrastructure ------------------------------------------ */
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

/* ---- Mutexes (38 total, one per MU block) ------------------------------ */
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
static pthread_mutex_t mutex_24 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_25 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_26 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_27 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_28 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_29 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_30 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_31 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_32 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_33 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_34 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_35 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_36 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_37 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_38 = PTHREAD_MUTEX_INITIALIZER;

/* ---- Semaphores (30 total) --------------------------------------------- *
 *
 * Expansion sems (sem_01..sem_15):
 *   sem posts after lane j-1 finishes layer k,
 *   lane j waits before starting layer k+1.
 *
 * Contraction sems (sem_16..sem_30):
 *   sem posts after lane j+1 finishes layer k,
 *   lane j waits before starting layer k+1.
 */
static sem_t sem_01;  /* lane1 L1  done -> lane2 before L2  */
static sem_t sem_02;  /* lane1 L2  done -> lane2 before L3  */
static sem_t sem_03;  /* lane2 L2  done -> lane3 before L3  */
static sem_t sem_04;  /* lane1 L3  done -> lane2 before L4  */
static sem_t sem_05;  /* lane2 L3  done -> lane3 before L4  */
static sem_t sem_06;  /* lane3 L3  done -> lane4 before L4  */
static sem_t sem_07;  /* lane1 L4  done -> lane2 before L5  */
static sem_t sem_08;  /* lane2 L4  done -> lane3 before L5  */
static sem_t sem_09;  /* lane3 L4  done -> lane4 before L5  */
static sem_t sem_10;  /* lane4 L4  done -> lane5 before L5  */
static sem_t sem_11;  /* lane1 L5  done -> lane2 before L6  */
static sem_t sem_12;  /* lane2 L5  done -> lane3 before L6  */
static sem_t sem_13;  /* lane3 L5  done -> lane4 before L6  */
static sem_t sem_14;  /* lane4 L5  done -> lane5 before L6  */
static sem_t sem_15;  /* lane5 L5  done -> lane6 before L6  */
static sem_t sem_16;  /* lane2 L6  done -> lane1 before L7  */
static sem_t sem_17;  /* lane3 L6  done -> lane2 before L7  */
static sem_t sem_18;  /* lane4 L6  done -> lane3 before L7  */
static sem_t sem_19;  /* lane5 L6  done -> lane4 before L7  */
static sem_t sem_20;  /* lane6 L6  done -> lane5 before L7  */
static sem_t sem_21;  /* lane2 L7  done -> lane1 before L8  */
static sem_t sem_22;  /* lane3 L7  done -> lane2 before L8  */
static sem_t sem_23;  /* lane4 L7  done -> lane3 before L8  */
static sem_t sem_24;  /* lane5 L7  done -> lane4 before L8  */
static sem_t sem_25;  /* lane2 L8  done -> lane1 before L9  */
static sem_t sem_26;  /* lane3 L8  done -> lane2 before L9  */
static sem_t sem_27;  /* lane4 L8  done -> lane3 before L9  */
static sem_t sem_28;  /* lane2 L9  done -> lane1 before L10 */
static sem_t sem_29;  /* lane3 L9  done -> lane2 before L10 */
static sem_t sem_30;  /* lane2 L10 done -> lane1 before L11 */

/* ---- Thread handles ---------------------------------------------------- */
static pthread_t t_lane1, t_lane2, t_lane3, t_lane4, t_lane5, t_lane6;

/* ---- Forward declarations ---------------------------------------------- */
static void *lane1_fn(void *arg);
static void *lane2_fn(void *arg);
static void *lane3_fn(void *arg);
static void *lane4_fn(void *arg);
static void *lane5_fn(void *arg);
static void *lane6_fn(void *arg);

/* ======================================================================== */
/*  lane1: L1 -> L2 -> ... -> L11  (leftmost column, 11 MU blocks)         */
/*  Expansion: posts to lane2 after each layer.                             */
/*  Contraction: waits for lane2 before each layer.                         */
/* ======================================================================== */
static void *lane1_fn(void *arg)
{
  /* L1 */
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
  sem_post(&sem_01);

  /* L2 */
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  sem_post(&sem_02);

  /* L3 */
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  sem_post(&sem_04);

  /* L4 */
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  sem_post(&sem_07);

  /* L5 */
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);
  sem_post(&sem_11);

  /* L6 (peak — no expansion post, start contraction waits) */
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);

  /* L7 */
  sem_wait(&sem_16);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_08);

  /* L8 */
  sem_wait(&sem_21);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_09);

  /* L9 */
  sem_wait(&sem_25);
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_10);

  /* L10 */
  sem_wait(&sem_28);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_11);

  /* L11 */
  sem_wait(&sem_30);
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_12);

  return NULL;
}

/* ======================================================================== */
/*  lane2: L2 -> L3 -> ... -> L10  (9 MU blocks)                           */
/*  Expansion: waits lane1, posts to lane3.                                 */
/*  Contraction: waits lane3, posts to lane1.                               */
/* ======================================================================== */
static void *lane2_fn(void *arg)
{
  /* L2 */
  sem_wait(&sem_01);
  pthread_mutex_lock(&mutex_13);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_13);
  sem_post(&sem_03);

  /* L3 */
  sem_wait(&sem_02);
  pthread_mutex_lock(&mutex_14);
  busy_wait_seconds(C14);
  pthread_mutex_unlock(&mutex_14);
  sem_post(&sem_05);

  /* L4 */
  sem_wait(&sem_04);
  pthread_mutex_lock(&mutex_15);
  busy_wait_seconds(C15);
  pthread_mutex_unlock(&mutex_15);
  sem_post(&sem_08);

  /* L5 */
  sem_wait(&sem_07);
  pthread_mutex_lock(&mutex_16);
  busy_wait_seconds(C16);
  pthread_mutex_unlock(&mutex_16);
  sem_post(&sem_12);

  /* L6 */
  sem_wait(&sem_11);
  pthread_mutex_lock(&mutex_17);
  busy_wait_seconds(C17);
  pthread_mutex_unlock(&mutex_17);
  sem_post(&sem_16);

  /* L7 */
  sem_wait(&sem_17);
  pthread_mutex_lock(&mutex_18);
  busy_wait_seconds(C18);
  pthread_mutex_unlock(&mutex_18);
  sem_post(&sem_21);

  /* L8 */
  sem_wait(&sem_22);
  pthread_mutex_lock(&mutex_19);
  busy_wait_seconds(C19);
  pthread_mutex_unlock(&mutex_19);
  sem_post(&sem_25);

  /* L9 */
  sem_wait(&sem_26);
  pthread_mutex_lock(&mutex_20);
  busy_wait_seconds(C20);
  pthread_mutex_unlock(&mutex_20);
  sem_post(&sem_28);

  /* L10 */
  sem_wait(&sem_29);
  pthread_mutex_lock(&mutex_21);
  busy_wait_seconds(C21);
  pthread_mutex_unlock(&mutex_21);
  sem_post(&sem_30);

  return NULL;
}

/* ======================================================================== */
/*  lane3: L3 -> L4 -> ... -> L9  (7 MU blocks)                            */
/*  Expansion: waits lane2, posts to lane4.                                 */
/*  Contraction: waits lane4, posts to lane2.                               */
/* ======================================================================== */
static void *lane3_fn(void *arg)
{
  /* L3 */
  sem_wait(&sem_03);
  pthread_mutex_lock(&mutex_22);
  busy_wait_seconds(C22);
  pthread_mutex_unlock(&mutex_22);
  sem_post(&sem_06);

  /* L4 */
  sem_wait(&sem_05);
  pthread_mutex_lock(&mutex_23);
  busy_wait_seconds(C23);
  pthread_mutex_unlock(&mutex_23);
  sem_post(&sem_09);

  /* L5 */
  sem_wait(&sem_08);
  pthread_mutex_lock(&mutex_24);
  busy_wait_seconds(C24);
  pthread_mutex_unlock(&mutex_24);
  sem_post(&sem_13);

  /* L6 */
  sem_wait(&sem_12);
  pthread_mutex_lock(&mutex_25);
  busy_wait_seconds(C25);
  pthread_mutex_unlock(&mutex_25);
  sem_post(&sem_17);

  /* L7 */
  sem_wait(&sem_18);
  pthread_mutex_lock(&mutex_26);
  busy_wait_seconds(C26);
  pthread_mutex_unlock(&mutex_26);
  sem_post(&sem_22);

  /* L8 */
  sem_wait(&sem_23);
  pthread_mutex_lock(&mutex_27);
  busy_wait_seconds(C27);
  pthread_mutex_unlock(&mutex_27);
  sem_post(&sem_26);

  /* L9 */
  sem_wait(&sem_27);
  pthread_mutex_lock(&mutex_28);
  busy_wait_seconds(C28);
  pthread_mutex_unlock(&mutex_28);
  sem_post(&sem_29);

  return NULL;
}

/* ======================================================================== */
/*  lane4: L4 -> L5 -> ... -> L8  (5 MU blocks)                            */
/*  Expansion: waits lane3, posts to lane5.                                 */
/*  Contraction: waits lane5, posts to lane3.                               */
/* ======================================================================== */
static void *lane4_fn(void *arg)
{
  /* L4 */
  sem_wait(&sem_06);
  pthread_mutex_lock(&mutex_29);
  busy_wait_seconds(C29);
  pthread_mutex_unlock(&mutex_29);
  sem_post(&sem_10);

  /* L5 */
  sem_wait(&sem_09);
  pthread_mutex_lock(&mutex_30);
  busy_wait_seconds(C30);
  pthread_mutex_unlock(&mutex_30);
  sem_post(&sem_14);

  /* L6 */
  sem_wait(&sem_13);
  pthread_mutex_lock(&mutex_31);
  busy_wait_seconds(C31);
  pthread_mutex_unlock(&mutex_31);
  sem_post(&sem_18);

  /* L7 */
  sem_wait(&sem_19);
  pthread_mutex_lock(&mutex_32);
  busy_wait_seconds(C32);
  pthread_mutex_unlock(&mutex_32);
  sem_post(&sem_23);

  /* L8 */
  sem_wait(&sem_24);
  pthread_mutex_lock(&mutex_33);
  busy_wait_seconds(C33);
  pthread_mutex_unlock(&mutex_33);
  sem_post(&sem_27);

  return NULL;
}

/* ======================================================================== */
/*  lane5: L5 -> L6 -> L7  (3 MU blocks)                                   */
/*  Expansion: waits lane4, posts to lane6.                                 */
/*  Contraction: waits lane6, posts to lane4.                               */
/* ======================================================================== */
static void *lane5_fn(void *arg)
{
  /* L5 */
  sem_wait(&sem_10);
  pthread_mutex_lock(&mutex_34);
  busy_wait_seconds(C34);
  pthread_mutex_unlock(&mutex_34);
  sem_post(&sem_15);

  /* L6 */
  sem_wait(&sem_14);
  pthread_mutex_lock(&mutex_35);
  busy_wait_seconds(C35);
  pthread_mutex_unlock(&mutex_35);
  sem_post(&sem_19);

  /* L7 */
  sem_wait(&sem_20);
  pthread_mutex_lock(&mutex_36);
  busy_wait_seconds(C36);
  pthread_mutex_unlock(&mutex_36);
  sem_post(&sem_24);

  return NULL;
}

/* ======================================================================== */
/*  lane6: L6 only  (1 MU block)                                           */
/*  Expansion: waits lane5.                                                 */
/*  Contraction: posts to lane5.                                            */
/* ======================================================================== */
static void *lane6_fn(void *arg)
{
  /* L6 */
  sem_wait(&sem_15);
  pthread_mutex_lock(&mutex_37);
  busy_wait_seconds(C37);
  pthread_mutex_unlock(&mutex_37);
  sem_post(&sem_20);

  return NULL;
}

/* ======================================================================== */
/*  main: init -> fork 6 lanes -> join 6 lanes -> final                     */
/* ======================================================================== */
int main(void)
{
  pthread_mutex_lock(&mutex_01);
  init_matrices();
  sem_init(&sem_01, 0, 0);
  sem_init(&sem_02, 0, 0);
  sem_init(&sem_03, 0, 0);
  sem_init(&sem_04, 0, 0);
  sem_init(&sem_05, 0, 0);
  sem_init(&sem_06, 0, 0);
  sem_init(&sem_07, 0, 0);
  sem_init(&sem_08, 0, 0);
  sem_init(&sem_09, 0, 0);
  sem_init(&sem_10, 0, 0);
  sem_init(&sem_11, 0, 0);
  sem_init(&sem_12, 0, 0);
  sem_init(&sem_13, 0, 0);
  sem_init(&sem_14, 0, 0);
  sem_init(&sem_15, 0, 0);
  sem_init(&sem_16, 0, 0);
  sem_init(&sem_17, 0, 0);
  sem_init(&sem_18, 0, 0);
  sem_init(&sem_19, 0, 0);
  sem_init(&sem_20, 0, 0);
  sem_init(&sem_21, 0, 0);
  sem_init(&sem_22, 0, 0);
  sem_init(&sem_23, 0, 0);
  sem_init(&sem_24, 0, 0);
  sem_init(&sem_25, 0, 0);
  sem_init(&sem_26, 0, 0);
  sem_init(&sem_27, 0, 0);
  sem_init(&sem_28, 0, 0);
  sem_init(&sem_29, 0, 0);
  sem_init(&sem_30, 0, 0);
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);

  pthread_create(&t_lane1, NULL, lane1_fn, NULL);
  pthread_create(&t_lane2, NULL, lane2_fn, NULL);
  pthread_create(&t_lane3, NULL, lane3_fn, NULL);
  pthread_create(&t_lane4, NULL, lane4_fn, NULL);
  pthread_create(&t_lane5, NULL, lane5_fn, NULL);
  pthread_create(&t_lane6, NULL, lane6_fn, NULL);

  pthread_join(t_lane1, NULL);
  pthread_join(t_lane2, NULL);
  pthread_join(t_lane3, NULL);
  pthread_join(t_lane4, NULL);
  pthread_join(t_lane5, NULL);
  pthread_join(t_lane6, NULL);

  pthread_mutex_lock(&mutex_38);
  busy_wait_seconds(C38);
  pthread_mutex_unlock(&mutex_38);
  return 0;
}
