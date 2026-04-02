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

/* zhang5 v3: 5 线程 (main + worker_a + filler_1/2/3), 8 个 MU 块, 0 个 sem
 *
 * 设计目标: 让 heft/t_level/wcet_first/zhao2020 优于 CFS/FIFO
 *
 * 策略: main 只做 fork/join 控制(极轻), 关键路径在 worker_a 上(最重任务)。
 * 3 个 filler 线程和 worker_a 同时竞争 2 核。
 *
 * CFS: 4 个 worker 均分 2 核, worker_a 得 50% CPU → 慢
 * 算法: worker_a 高优先级独占 1 核, filler 共享另 1 核 → 快
 *
 * DAG:
 *   main#001(C1=轻) -> fork all -> join(worker_a) -> join(f1,f2,f3) -> main#002(C2=轻)
 *
 *   worker_a:   worker_a#001(C3=重) → worker_a#002(C4=重)
 *   filler_1:   filler_1#001(C5=重)
 *   filler_2:   filler_2#001(C6=重)
 *   filler_3:   filler_3#001(C7=重)
 *
 * 关键路径: main#001 → worker_a#001 → worker_a#002 → main(join) → main#002
 * worker_a 总量 = C3+C4 = 10, filler 各 4, main 极轻
 *
 * 2核下:
 *   算法: worker_a 独占1核跑10单位, 3个filler共享另1核跑12单位(串行)
 *         总时间 = max(10, 12) = 12 单位
 *   CFS:  4线程均分2核, worker_a 得 0.5 核, 跑完需 10/0.5=20 单位
 *         总时间 = 20 单位
 *   差距: 20/12 ≈ 1.67x
 */

#define C1  0.3     /* main#001: 极轻, fork 前 */
#define C2  0.3     /* main#002: 极轻, 收尾 */
#define C3  5.0     /* worker_a#001: 关键路径, 重 */
#define C4  5.0     /* worker_a#002: 关键路径, 重 */
#define C5  4.0     /* filler_1#001: 填充 */
#define C6  4.0     /* filler_2#001: 填充 */
#define C7  4.0     /* filler_3#001: 填充 */
#define C8  4.0     /* filler_1#002: 填充第二段 */

static void *worker_a(void *arg);
static void *filler_1(void *arg);
static void *filler_2(void *arg);
static void *filler_3(void *arg);

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

/* --- 同步原语 --- */
static pthread_mutex_t mutex_01 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_02 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_03 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_04 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_05 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_06 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_07 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_08 = PTHREAD_MUTEX_INITIALIZER;

static pthread_t thread_a, thread_f1, thread_f2, thread_f3;

/* --- worker_a: C3 → C4 (关键路径, 最重) --- */
static void *worker_a(void *arg) {
  l1_set_thread_prio_fifo(96);
  (void)arg;
  l1_set_thread_prio_fifo(95);
  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);
  l1_set_thread_prio_fifo(88);
  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);
  return NULL;
}

/* --- filler_1: C5 → C8 --- */
static void *filler_1(void *arg) {
  l1_set_thread_prio_fifo(94);
  (void)arg;
  l1_set_thread_prio_fifo(93);
  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);
  l1_set_thread_prio_fifo(87);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_08);
  return NULL;
}

/* --- filler_2: C6 --- */
static void *filler_2(void *arg) {
  l1_set_thread_prio_fifo(92);
  (void)arg;
  l1_set_thread_prio_fifo(91);
  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);
  return NULL;
}

/* --- filler_3: C7 --- */
static void *filler_3(void *arg) {
  l1_set_thread_prio_fifo(90);
  (void)arg;
  l1_set_thread_prio_fifo(89);
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);
  return NULL;
}

/* --- main --- */
int main(void) {
  l1_set_thread_prio_fifo(99);
  init_matrices();

  /* main#001: 极轻 */
  l1_set_thread_prio_fifo(98);
  pthread_mutex_lock(&mutex_01);
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);
l1_set_thread_prio_fifo(97);

  /* fork all */
  pthread_create(&thread_a, NULL, worker_a, NULL);
  pthread_create(&thread_f1, NULL, filler_1, NULL);
  pthread_create(&thread_f2, NULL, filler_2, NULL);
  pthread_create(&thread_f3, NULL, filler_3, NULL);
l1_set_thread_prio_fifo(86);

  /* join: 先 worker_a(关键路径), 再 filler */
  l1_set_thread_prio_fifo(85);
  pthread_join(thread_a, NULL);
  pthread_join(thread_f1, NULL);
  pthread_join(thread_f2, NULL);
  pthread_join(thread_f3, NULL);

  /* main#002: 极轻, 收尾 */
  l1_set_thread_prio_fifo(84);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);
l1_set_thread_prio_fifo(83);

  return 0;
}
