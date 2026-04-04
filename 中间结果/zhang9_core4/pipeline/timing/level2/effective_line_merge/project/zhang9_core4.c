#define _GNU_SOURCE
#include "segtrace.h"
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
  pthread_mutex_lock(&mutex_27);
SEG_BEGIN("MU:tail_worker_1#001@115-118");
  busy_wait_seconds(C27);
SEG_END("MU:tail_worker_1#001@115-118");
  pthread_mutex_unlock(&mutex_27);

  return NULL;
}

static void *tail_worker_2(void *arg)
{
  pthread_mutex_lock(&mutex_28);
SEG_BEGIN("MU:tail_worker_2#001@124-127");
  busy_wait_seconds(C28);
SEG_END("MU:tail_worker_2#001@124-127");
  pthread_mutex_unlock(&mutex_28);

  return NULL;
}

static void *tail_worker_3(void *arg)
{
  pthread_mutex_lock(&mutex_29);
SEG_BEGIN("MU:tail_worker_3#001@133-136");
  busy_wait_seconds(C29);
SEG_END("MU:tail_worker_3#001@133-136");
  pthread_mutex_unlock(&mutex_29);

  return NULL;
}

static void *tail_worker_4(void *arg)
{
  pthread_mutex_lock(&mutex_30);
SEG_BEGIN("MU:tail_worker_4#001@142-145");
  busy_wait_seconds(C30);
SEG_END("MU:tail_worker_4#001@142-145");
  pthread_mutex_unlock(&mutex_30);

  return NULL;
}

static void *gate_worker_1(void *arg)
{
  pthread_mutex_lock(&mutex_19);
SEG_BEGIN("MU:gate_worker_1#001@151-154");
  busy_wait_seconds(C19);
SEG_END("MU:gate_worker_1#001@151-154");
  pthread_mutex_unlock(&mutex_19);
  pthread_create(&thread_tail_1, NULL, tail_worker_1, NULL);
  pthread_mutex_lock(&mutex_20);
SEG_BEGIN("MU:gate_worker_1#002@155-158");
  busy_wait_seconds(C20);
SEG_END("MU:gate_worker_1#002@155-158");
  pthread_mutex_unlock(&mutex_20);

  return NULL;
}

static void *gate_worker_2(void *arg)
{
  pthread_mutex_lock(&mutex_21);
SEG_BEGIN("MU:gate_worker_2#001@164-167");
  busy_wait_seconds(C21);
SEG_END("MU:gate_worker_2#001@164-167");
  pthread_mutex_unlock(&mutex_21);
  pthread_create(&thread_tail_2, NULL, tail_worker_2, NULL);
  pthread_mutex_lock(&mutex_22);
SEG_BEGIN("MU:gate_worker_2#002@168-171");
  busy_wait_seconds(C22);
SEG_END("MU:gate_worker_2#002@168-171");
  pthread_mutex_unlock(&mutex_22);

  return NULL;
}

static void *gate_worker_3(void *arg)
{
  pthread_mutex_lock(&mutex_23);
SEG_BEGIN("MU:gate_worker_3#001@177-180");
  busy_wait_seconds(C23);
SEG_END("MU:gate_worker_3#001@177-180");
  pthread_mutex_unlock(&mutex_23);
  pthread_create(&thread_tail_3, NULL, tail_worker_3, NULL);
  pthread_mutex_lock(&mutex_24);
SEG_BEGIN("MU:gate_worker_3#002@181-184");
  busy_wait_seconds(C24);
SEG_END("MU:gate_worker_3#002@181-184");
  pthread_mutex_unlock(&mutex_24);

  return NULL;
}

static void *gate_worker_4(void *arg)
{
  pthread_mutex_lock(&mutex_25);
SEG_BEGIN("MU:gate_worker_4#001@190-193");
  busy_wait_seconds(C25);
SEG_END("MU:gate_worker_4#001@190-193");
  pthread_mutex_unlock(&mutex_25);
  pthread_create(&thread_tail_4, NULL, tail_worker_4, NULL);
  pthread_mutex_lock(&mutex_26);
SEG_BEGIN("MU:gate_worker_4#002@194-197");
  busy_wait_seconds(C26);
SEG_END("MU:gate_worker_4#002@194-197");
  pthread_mutex_unlock(&mutex_26);

  return NULL;
}

static void *launcher_l(void *arg)
{
  pthread_mutex_lock(&mutex_15);
SEG_BEGIN("MU:launcher_l#001@203-207");
  busy_wait_seconds(C15);
SEG_END("MU:launcher_l#001@203-207");
  pthread_mutex_unlock(&mutex_15);
  pthread_create(&thread_gate_1, NULL, gate_worker_1, NULL);
  pthread_create(&thread_gate_2, NULL, gate_worker_2, NULL);
  pthread_mutex_lock(&mutex_16);
SEG_BEGIN("MU:launcher_l#002@208-211");
  busy_wait_seconds(C16);
SEG_END("MU:launcher_l#002@208-211");
  pthread_mutex_unlock(&mutex_16);

  return NULL;
}

static void *launcher_r(void *arg)
{
  pthread_mutex_lock(&mutex_17);
SEG_BEGIN("MU:launcher_r#001@217-221");
  busy_wait_seconds(C17);
SEG_END("MU:launcher_r#001@217-221");
  pthread_mutex_unlock(&mutex_17);
  pthread_create(&thread_gate_3, NULL, gate_worker_3, NULL);
  pthread_create(&thread_gate_4, NULL, gate_worker_4, NULL);
  pthread_mutex_lock(&mutex_18);
SEG_BEGIN("MU:launcher_r#002@222-225");
  busy_wait_seconds(C18);
SEG_END("MU:launcher_r#002@222-225");
  pthread_mutex_unlock(&mutex_18);

  return NULL;
}

static void *blocker_a(void *arg)
{
  pthread_mutex_lock(&mutex_07);
SEG_BEGIN("MU:blocker_a#001@231-233");
  busy_wait_seconds(C7);
SEG_END("MU:blocker_a#001@231-233");
  pthread_mutex_unlock(&mutex_07);
  pthread_mutex_lock(&mutex_08);
SEG_BEGIN("MU:blocker_a#002@234-237");
  busy_wait_seconds(C8);
SEG_END("MU:blocker_a#002@234-237");
  pthread_mutex_unlock(&mutex_08);

  return NULL;
}

static void *blocker_b(void *arg)
{
  pthread_mutex_lock(&mutex_09);
SEG_BEGIN("MU:blocker_b#001@243-245");
  busy_wait_seconds(C9);
SEG_END("MU:blocker_b#001@243-245");
  pthread_mutex_unlock(&mutex_09);
  pthread_mutex_lock(&mutex_10);
SEG_BEGIN("MU:blocker_b#002@246-249");
  busy_wait_seconds(C10);
SEG_END("MU:blocker_b#002@246-249");
  pthread_mutex_unlock(&mutex_10);

  return NULL;
}

static void *blocker_c(void *arg)
{
  pthread_mutex_lock(&mutex_11);
SEG_BEGIN("MU:blocker_c#001@255-257");
  busy_wait_seconds(C11);
SEG_END("MU:blocker_c#001@255-257");
  pthread_mutex_unlock(&mutex_11);
  pthread_mutex_lock(&mutex_12);
SEG_BEGIN("MU:blocker_c#002@258-261");
  busy_wait_seconds(C12);
SEG_END("MU:blocker_c#002@258-261");
  pthread_mutex_unlock(&mutex_12);

  return NULL;
}

static void *blocker_d(void *arg)
{
  pthread_mutex_lock(&mutex_13);
SEG_BEGIN("MU:blocker_d#001@267-269");
  busy_wait_seconds(C13);
SEG_END("MU:blocker_d#001@267-269");
  pthread_mutex_unlock(&mutex_13);
  pthread_mutex_lock(&mutex_14);
SEG_BEGIN("MU:blocker_d#002@270-273");
  busy_wait_seconds(C14);
SEG_END("MU:blocker_d#002@270-273");
  pthread_mutex_unlock(&mutex_14);

  return NULL;
}

int main(void)
{
  pthread_mutex_lock(&mutex_01);
SEG_BEGIN("MU:main#001@279-299");
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
SEG_END("MU:main#001@279-299");
  pthread_mutex_unlock(&mutex_01);

  pthread_create(&thread_blocker_a, NULL, blocker_a, NULL);
  pthread_create(&thread_blocker_b, NULL, blocker_b, NULL);
  pthread_create(&thread_blocker_c, NULL, blocker_c, NULL);
  pthread_create(&thread_blocker_d, NULL, blocker_d, NULL);
  pthread_create(&thread_launcher_l, NULL, launcher_l, NULL);
  pthread_create(&thread_launcher_r, NULL, launcher_r, NULL);

  pthread_mutex_lock(&mutex_02);
SEG_BEGIN("MU:main#002@300-303");
  busy_wait_seconds(C2);
SEG_END("MU:main#002@300-303");
  pthread_mutex_unlock(&mutex_02);

  pthread_join(thread_launcher_l, NULL);
  pthread_join(thread_launcher_r, NULL);

  pthread_mutex_lock(&mutex_03);
SEG_BEGIN("MU:main#003@304-310");
  busy_wait_seconds(C3);
SEG_END("MU:main#003@304-310");
  pthread_mutex_unlock(&mutex_03);

  pthread_join(thread_gate_1, NULL);
  pthread_join(thread_gate_2, NULL);
  pthread_join(thread_gate_3, NULL);
  pthread_join(thread_gate_4, NULL);

  pthread_mutex_lock(&mutex_04);
SEG_BEGIN("MU:main#004@311-319");
  busy_wait_seconds(C4);
SEG_END("MU:main#004@311-319");
  pthread_mutex_unlock(&mutex_04);

  pthread_join(thread_tail_1, NULL);
  pthread_join(thread_tail_2, NULL);
  pthread_join(thread_tail_3, NULL);
  pthread_join(thread_tail_4, NULL);

  pthread_mutex_lock(&mutex_05);
SEG_BEGIN("MU:main#005@320-328");
  busy_wait_seconds(C5);
SEG_END("MU:main#005@320-328");
  pthread_mutex_unlock(&mutex_05);

  pthread_join(thread_blocker_a, NULL);
  pthread_join(thread_blocker_b, NULL);
  pthread_join(thread_blocker_c, NULL);
  pthread_join(thread_blocker_d, NULL);

  pthread_mutex_lock(&mutex_06);
SEG_BEGIN("MU:main#006@329-337");
  busy_wait_seconds(C6);
SEG_END("MU:main#006@329-337");
  pthread_mutex_unlock(&mutex_06);

  return 0;
}
