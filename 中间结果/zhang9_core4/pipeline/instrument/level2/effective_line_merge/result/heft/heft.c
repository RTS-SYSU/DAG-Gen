#define _GNU_SOURCE
#include "prio_runtime.h"
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/*
 * 权重策略（4 核 + CFS 对照）：
 * - 4 个 blocker 从启动即长跑，首段权重大（C7/C9/C11/C13），与 launcher、gate、tail
 *   在「多就绪线程抢 4 核」窗口持续竞争。
 * - CFS 公平轮转 → 关键路径（launcher→gate→tail）与 blocker 均分核时间 →
 *   launcher/gate/tail 启动偏晚，尾部 C27–C30 权重又大，总 makespan 明显拉长。
 * - FIFO/启发式若抬高关键链优先级，可先推进 tail，blocker 最后被 join，更占优。
 * 忙等：同名宏 busy_wait_seconds，与 zhang9 一致，ARM 虚拟计数器 + WORK_SCALE。
 */

#define C1 18.0
#define C2 28.0
#define C3 22.0
#define C4 22.0
#define C5 16.0
#define C6 12.0
#define C7 2900.0
#define C8 480.0
#define C9 2700.0
#define C10 460.0
#define C11 2500.0
#define C12 440.0
#define C13 2300.0
#define C14 420.0
#define C15 1550.0
#define C16 22.0
#define C17 1450.0
#define C18 22.0
#define C19 48.0
#define C20 36.0
#define C21 47.0
#define C22 35.0
#define C23 46.0
#define C24 34.0
#define C25 45.0
#define C26 33.0
#define C27 4200.0
#define C28 3800.0
#define C29 3400.0
#define C30 3000.0

#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

#define busy_wait_seconds(weight) \
  do { \
    unsigned long long _bw_freq, _bw_start, _bw_now; \
    __asm__ __volatile__("mrs %0, cntfrq_el0" : "=r"(_bw_freq)); \
    unsigned long long _bw_ticks = (unsigned long long)((weight) * WORK_SCALE * 1e-5 * (double)_bw_freq); \
    __asm__ __volatile__("mrs %0, cntvct_el0" : "=r"(_bw_start)); \
    for (;;) { \
      __asm__ __volatile__("mrs %0, cntvct_el0" : "=r"(_bw_now)); \
      if (_bw_now - _bw_start >= _bw_ticks) break; \
    } \
  } while (0)

static pthread_t thread_blocker_a;
static pthread_t thread_blocker_b;
static pthread_t thread_blocker_c;
static pthread_t thread_blocker_d;
static pthread_t thread_launcher_l;
static pthread_t thread_launcher_r;
static pthread_t thread_gate_1;
static pthread_t thread_gate_2;
static pthread_t thread_gate_3;
static pthread_t thread_gate_4;
static pthread_t thread_tail_1;
static pthread_t thread_tail_2;
static pthread_t thread_tail_3;
static pthread_t thread_tail_4;

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

static void *tail_worker_1(void *arg)
{
  l1_set_thread_prio_fifo(95);
  pthread_mutex_lock(&mutex_27);
  busy_wait_seconds(C27);
  pthread_mutex_unlock(&mutex_27);

  return NULL;
}

static void *tail_worker_2(void *arg)
{
  l1_set_thread_prio_fifo(93);
  pthread_mutex_lock(&mutex_28);
  busy_wait_seconds(C28);
  pthread_mutex_unlock(&mutex_28);

  return NULL;
}

static void *tail_worker_3(void *arg)
{
  l1_set_thread_prio_fifo(91);
  pthread_mutex_lock(&mutex_29);
  busy_wait_seconds(C29);
  pthread_mutex_unlock(&mutex_29);

  return NULL;
}

static void *tail_worker_4(void *arg)
{
  l1_set_thread_prio_fifo(87);
  pthread_mutex_lock(&mutex_30);
  busy_wait_seconds(C30);
  pthread_mutex_unlock(&mutex_30);

  return NULL;
}

static void *gate_worker_1(void *arg)
{
  l1_set_thread_prio_fifo(96);
  pthread_mutex_lock(&mutex_19);
  busy_wait_seconds(C19);
  pthread_mutex_unlock(&mutex_19);
  pthread_create(&thread_tail_1, NULL, tail_worker_1, NULL);
  l1_set_thread_prio_fifo(76);
  pthread_mutex_lock(&mutex_20);
  busy_wait_seconds(C20);
  pthread_mutex_unlock(&mutex_20);

  return NULL;
}

static void *gate_worker_2(void *arg)
{
  l1_set_thread_prio_fifo(94);
  pthread_mutex_lock(&mutex_21);
  busy_wait_seconds(C21);
  pthread_mutex_unlock(&mutex_21);
  pthread_create(&thread_tail_2, NULL, tail_worker_2, NULL);
  l1_set_thread_prio_fifo(77);
  pthread_mutex_lock(&mutex_22);
  busy_wait_seconds(C22);
  pthread_mutex_unlock(&mutex_22);

  return NULL;
}

static void *gate_worker_3(void *arg)
{
  l1_set_thread_prio_fifo(92);
  pthread_mutex_lock(&mutex_23);
  busy_wait_seconds(C23);
  pthread_mutex_unlock(&mutex_23);
  pthread_create(&thread_tail_3, NULL, tail_worker_3, NULL);
  l1_set_thread_prio_fifo(75);
  pthread_mutex_lock(&mutex_24);
  busy_wait_seconds(C24);
  pthread_mutex_unlock(&mutex_24);

  return NULL;
}

static void *gate_worker_4(void *arg)
{
  l1_set_thread_prio_fifo(88);
  pthread_mutex_lock(&mutex_25);
  busy_wait_seconds(C25);
  pthread_mutex_unlock(&mutex_25);
  pthread_create(&thread_tail_4, NULL, tail_worker_4, NULL);
  l1_set_thread_prio_fifo(74);
  pthread_mutex_lock(&mutex_26);
  busy_wait_seconds(C26);
  pthread_mutex_unlock(&mutex_26);

  return NULL;
}

static void *launcher_l(void *arg)
{
  l1_set_thread_prio_fifo(98);
  pthread_mutex_lock(&mutex_15);
  busy_wait_seconds(C15);
  pthread_mutex_unlock(&mutex_15);
  pthread_create(&thread_gate_1, NULL, gate_worker_1, NULL);
  pthread_create(&thread_gate_2, NULL, gate_worker_2, NULL);
  l1_set_thread_prio_fifo(79);
  pthread_mutex_lock(&mutex_16);
  busy_wait_seconds(C16);
  pthread_mutex_unlock(&mutex_16);

  return NULL;
}

static void *launcher_r(void *arg)
{
  l1_set_thread_prio_fifo(97);
  pthread_mutex_lock(&mutex_17);
  busy_wait_seconds(C17);
  pthread_mutex_unlock(&mutex_17);
  pthread_create(&thread_gate_3, NULL, gate_worker_3, NULL);
  pthread_create(&thread_gate_4, NULL, gate_worker_4, NULL);
  l1_set_thread_prio_fifo(78);
  pthread_mutex_lock(&mutex_18);
  busy_wait_seconds(C18);
  pthread_mutex_unlock(&mutex_18);

  return NULL;
}

static void *blocker_a(void *arg)
{
  l1_set_thread_prio_fifo(90);
  pthread_mutex_lock(&mutex_07);
  busy_wait_seconds(C7);
  pthread_mutex_unlock(&mutex_07);
  l1_set_thread_prio_fifo(84);
  pthread_mutex_lock(&mutex_08);
  busy_wait_seconds(C8);
  pthread_mutex_unlock(&mutex_08);

  return NULL;
}

static void *blocker_b(void *arg)
{
  l1_set_thread_prio_fifo(89);
  pthread_mutex_lock(&mutex_09);
  busy_wait_seconds(C9);
  pthread_mutex_unlock(&mutex_09);
  l1_set_thread_prio_fifo(83);
  pthread_mutex_lock(&mutex_10);
  busy_wait_seconds(C10);
  pthread_mutex_unlock(&mutex_10);

  return NULL;
}

static void *blocker_c(void *arg)
{
  l1_set_thread_prio_fifo(86);
  pthread_mutex_lock(&mutex_11);
  busy_wait_seconds(C11);
  pthread_mutex_unlock(&mutex_11);
  l1_set_thread_prio_fifo(82);
  pthread_mutex_lock(&mutex_12);
  busy_wait_seconds(C12);
  pthread_mutex_unlock(&mutex_12);

  return NULL;
}

static void *blocker_d(void *arg)
{
  l1_set_thread_prio_fifo(85);
  pthread_mutex_lock(&mutex_13);
  busy_wait_seconds(C13);
  pthread_mutex_unlock(&mutex_13);
  l1_set_thread_prio_fifo(81);
  pthread_mutex_lock(&mutex_14);
  busy_wait_seconds(C14);
  pthread_mutex_unlock(&mutex_14);

  return NULL;
}

int main(void)
{
  l1_set_thread_prio_fifo(99);
  pthread_mutex_lock(&mutex_01);
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(4, &cpu_set);
  CPU_SET(5, &cpu_set);
  CPU_SET(6, &cpu_set);
  CPU_SET(7, &cpu_set);
  if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0)
  {
    fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
  }
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mutex_01);

  pthread_create(&thread_blocker_a, NULL, blocker_a, NULL);
  pthread_create(&thread_blocker_b, NULL, blocker_b, NULL);
  pthread_create(&thread_blocker_c, NULL, blocker_c, NULL);
  pthread_create(&thread_blocker_d, NULL, blocker_d, NULL);
  pthread_create(&thread_launcher_l, NULL, launcher_l, NULL);
  pthread_create(&thread_launcher_r, NULL, launcher_r, NULL);

  l1_set_thread_prio_fifo(80);
  pthread_mutex_lock(&mutex_02);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mutex_02);

  l1_set_thread_prio_fifo(73);
  pthread_join(thread_launcher_l, NULL);
  pthread_join(thread_launcher_r, NULL);

  pthread_mutex_lock(&mutex_03);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mutex_03);

  l1_set_thread_prio_fifo(72);
  pthread_join(thread_gate_1, NULL);
  pthread_join(thread_gate_2, NULL);
  pthread_join(thread_gate_3, NULL);
  pthread_join(thread_gate_4, NULL);

  pthread_mutex_lock(&mutex_04);
  busy_wait_seconds(C4);
  pthread_mutex_unlock(&mutex_04);

  l1_set_thread_prio_fifo(71);
  pthread_join(thread_tail_1, NULL);
  pthread_join(thread_tail_2, NULL);
  pthread_join(thread_tail_3, NULL);
  pthread_join(thread_tail_4, NULL);

  pthread_mutex_lock(&mutex_05);
  busy_wait_seconds(C5);
  pthread_mutex_unlock(&mutex_05);

  l1_set_thread_prio_fifo(70);
  pthread_join(thread_blocker_a, NULL);
  pthread_join(thread_blocker_b, NULL);
  pthread_join(thread_blocker_c, NULL);
  pthread_join(thread_blocker_d, NULL);

  pthread_mutex_lock(&mutex_06);
  busy_wait_seconds(C6);
  pthread_mutex_unlock(&mutex_06);

  return 0;
}
