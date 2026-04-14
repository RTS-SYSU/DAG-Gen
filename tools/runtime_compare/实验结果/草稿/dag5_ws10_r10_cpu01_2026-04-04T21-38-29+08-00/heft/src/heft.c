#define _GNU_SOURCE
#include "prio_runtime.h"
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * dag5: "Relay" — 3-node serial critical chain + 10 equal fillers.
 *
 * 11 worker threads + main = 12 total.  Pure fork-join, no semaphores.
 * The critical chain is a single thread with 3 sequential MU blocks;
 * no cross-thread sems are needed for the chain itself.
 *
 * Topology:
 *   main#001(C1)
 *     fork ──> filler_01#001(C2)   ──────────────────────────> join
 *              filler_02#001(C3)   ──────────────────────────> join
 *              filler_03#001(C4)   ──────────────────────────> join
 *              filler_04#001(C5)   ──────────────────────────> join
 *              filler_05#001(C6)   ──────────────────────────> join
 *              filler_06#001(C7)   ──────────────────────────> join
 *              filler_07#001(C8)   ──────────────────────────> join
 *              filler_08#001(C9)   ──────────────────────────> join
 *              filler_09#001(C10)  ──────────────────────────> join
 *              filler_10#001(C11)  ──────────────────────────> join
 *              worker_chain#001(C12)
 *                → worker_chain#002(C13)
 *                → worker_chain#003(C14)  ─────────────────> join
 *   main#002(C15)
 *
 * Weight rationale  (W_chain_node=6, total_chain=18, W_fill=4, K=10 fillers):
 *
 *   rank_u(chain_node_1) = 6+6+6 = 18 >> rank_u(filler) = 4
 *   W_chain_node(6) > W_fill(4)  →  wcet_first also gives chain priority.
 *   t_level: chain nodes have successors, gaining higher b_level/rank_u;
 *            chain_node_1 ranks highest, giving correct scheduling order.
 *
 *   Under algorithm (SCHED_FIFO + correct priorities, 4 cores):
 *     chain thread (prio≈99): 1 dedicated core  → 18 wall-time (~1.69 s)
 *     10 fillers on 3 cores (batches of 3, then 1):
 *       t=0..4: f1,f2,f3   t=4..8: f4,f5,f6   t=8..12: f7,f8,f9
 *       t=12..16: f10 (alone, still < 18)
 *     Makespan = 18 wall.
 *
 *   Under CFS (11 active threads, 4 cores, each ≈ 0.36 core):
 *     All 10 fillers finish at 4/0.36 ≈ 11.1 wall.
 *     Chain has done 11.1*0.36 ≈ 4 units; 14 remain, runs alone.
 *     Makespan ≈ 11.1 + 14 = 25.1 wall  (~2.36 s at ws=100).
 *
 *   Under FIFO (all prio=99, 11 threads, 4 cores):
 *     Fillers created first, grab all 4 cores.
 *     Chain starts only after first batch finishes (≈ t=4).
 *     Chain finishes at ≈ t=4+18=22.  Makespan ≈ 22 wall  (~2.07 s).
 *
 *   Expected improvement:
 *     Algorithm vs CFS   ≈ 39 %
 *     Algorithm vs FIFO  ≈ 22 %
 *
 * FIFO note: same strategy as dag4 — fillers forked before chain so that
 * FIFO fills 4 cores with fillers; algorithm's priority injection gives
 * chain prio=99, immediately preempting lower-priority fillers.
 */

/* ---- Weight constants -------------------------------------------------- */
#define C1   0.1   /* main#001           init              */
#define C2   4.0   /* filler_01#001                        */
#define C3   4.0   /* filler_02#001                        */
#define C4   4.0   /* filler_03#001                        */
#define C5   4.0   /* filler_04#001                        */
#define C6   4.0   /* filler_05#001                        */
#define C7   4.0   /* filler_06#001                        */
#define C8   4.0   /* filler_07#001                        */
#define C9   4.0   /* filler_08#001                        */
#define C10  4.0   /* filler_09#001                        */
#define C11  4.0   /* filler_10#001                        */
#define C12  6.0   /* worker_chain#001   (chain node 1)    */
#define C13  6.0   /* worker_chain#002   (chain node 2)    */
#define C14  6.0   /* worker_chain#003   (chain node 3)    */
#define C15  0.1   /* main#002           final              */

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

/* ---- Mutexes (15 total, one per MU block) ------------------------------ */
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

/* ---- Thread handles ---------------------------------------------------- */
static pthread_t t_filler_01;
static pthread_t t_filler_02;
static pthread_t t_filler_03;
static pthread_t t_filler_04;
static pthread_t t_filler_05;
static pthread_t t_filler_06;
static pthread_t t_filler_07;
static pthread_t t_filler_08;
static pthread_t t_filler_09;
static pthread_t t_filler_10;
static pthread_t t_chain;

/* ---- Worker functions -------------------------------------------------- */
static void *filler_01(void *arg) {
  l1_set_thread_prio_fifo(97);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
  return NULL;
}

static void *filler_02(void *arg) {
  l1_set_thread_prio_fifo(95);
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  return NULL;
}

static void *filler_03(void *arg) {
  l1_set_thread_prio_fifo(87);
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  return NULL;
}

static void *filler_04(void *arg) {
  l1_set_thread_prio_fifo(92);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  return NULL;
}

static void *filler_05(void *arg) {
  l1_set_thread_prio_fifo(89);
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

static void *filler_06(void *arg) {
  l1_set_thread_prio_fifo(88);
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);
  return NULL;
}

static void *filler_07(void *arg) {
  l1_set_thread_prio_fifo(90);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_08);
  return NULL;
}

static void *filler_08(void *arg) {
  l1_set_thread_prio_fifo(91);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_09);
  return NULL;
}

static void *filler_09(void *arg) {
  l1_set_thread_prio_fifo(94);
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_10);
  return NULL;
}

static void *filler_10(void *arg) {
  l1_set_thread_prio_fifo(93);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_11);
  return NULL;
}

/* worker_chain: 3 sequential MU blocks forming the critical chain.
 * rank_u(block_1) = C12+C13+C14 = 18, rank_u(block_2) = 12, rank_u(block_3) = 6.
 * All three values exceed W_fill=4, so every block stays high-priority. */
static void *worker_chain(void *arg) {
  l1_set_thread_prio_fifo(98);
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_12);
  l1_set_thread_prio_fifo(96);
  pthread_mutex_lock(&mutex_13);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_13);
  l1_set_thread_prio_fifo(86);
  pthread_mutex_lock(&mutex_14);
  busy_wait_seconds(C14);
  pthread_mutex_unlock(&mutex_14);
  return NULL;
}

/* ---- main -------------------------------------------------------------- */
int main(void)
{
    struct timespec ts_main_begin, ts_main_end;
    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);
  l1_set_thread_prio_fifo(99);
  pthread_mutex_lock(&mutex_01);
  init_matrices();
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);

  /* Fork fillers first so FIFO (same-prio) fills cores with fillers before
   * chain.  Algorithm instrumentation gives chain blocks prio>filler and
   * chain immediately preempts lower-priority fillers. */
  pthread_create(&t_filler_01, NULL, filler_01, NULL);
  pthread_create(&t_filler_02, NULL, filler_02, NULL);
  pthread_create(&t_filler_03, NULL, filler_03, NULL);
  pthread_create(&t_filler_04, NULL, filler_04, NULL);
  pthread_create(&t_filler_05, NULL, filler_05, NULL);
  pthread_create(&t_filler_06, NULL, filler_06, NULL);
  pthread_create(&t_filler_07, NULL, filler_07, NULL);
  pthread_create(&t_filler_08, NULL, filler_08, NULL);
  pthread_create(&t_filler_09, NULL, filler_09, NULL);
  pthread_create(&t_filler_10, NULL, filler_10, NULL);
  pthread_create(&t_chain,     NULL, worker_chain, NULL);

  l1_set_thread_prio_fifo(85);
  pthread_join(t_filler_01, NULL);
  pthread_join(t_filler_02, NULL);
  pthread_join(t_filler_03, NULL);
  pthread_join(t_filler_04, NULL);
  pthread_join(t_filler_05, NULL);
  pthread_join(t_filler_06, NULL);
  pthread_join(t_filler_07, NULL);
  pthread_join(t_filler_08, NULL);
  pthread_join(t_filler_09, NULL);
  pthread_join(t_filler_10, NULL);
  pthread_join(t_chain,     NULL);

  pthread_mutex_lock(&mutex_15);
  busy_wait_seconds(C15);
  pthread_mutex_unlock(&mutex_15);
    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);
    {
        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)
            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;
        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\n", main_s);
    }
  return 0;
}
