#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define C1 160.0
#define C2 180.0
#define C3 150.0
#define F1 140.0
#define F2 120.0
#define TAIL 20.0

#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 25000
#endif

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];
static volatile double g_busy_sink = 0.0;

static pthread_t th_fill_1;
static pthread_t th_fill_2;
static pthread_t th_crit_1;
static pthread_t th_crit_2;
static pthread_t th_crit_3;

static sem_t sem_c12;
static sem_t sem_c23;

static pthread_mutex_t mu_fill_1 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mu_fill_2 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mu_crit_1 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mu_crit_2 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mu_crit_3 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mu_tail = PTHREAD_MUTEX_INITIALIZER;

static void init_matrices(void) {
  for (int i = 0; i < MAT_N; ++i) {
    for (int j = 0; j < MAT_N; ++j) {
      mat_a[i][j] = (double)(i + j + 1);
      mat_b[i][j] = (double)(i * 3 + j + 5);
      mat_c[i][j] = 0.0;
    }
  }
}

static void busy_wait_seconds(double seconds) {
  int units = (int)(seconds * WORK_SCALE + 0.5);
  if (units < 1)
    units = 1;

  double x = 1.000001;
  double y = 0.999999;
  double z = 1.0000003;
  double acc = 0.0;

  for (int r = 0; r < units; ++r) {
    for (int i = 0; i < 512; ++i) {
      x = x * 1.0000001 + y * 0.9999999 + z * 0.0000001;
      y = y * 1.0000002 + z * 0.9999998 + x * 0.0000002;
      z = z * 1.0000003 + x * 0.9999997 + y * 0.0000003;
      acc += x * y + z;
    }
  }

  g_busy_sink += acc;
  mat_c[0][0] = g_busy_sink;
}

static void *fill_worker_1(void *arg) {
  (void)arg;
  pthread_mutex_lock(&mu_fill_1);
  busy_wait_seconds(F1);
  pthread_mutex_unlock(&mu_fill_1);
  return NULL;
}

static void *fill_worker_2(void *arg) {
  (void)arg;
  pthread_mutex_lock(&mu_fill_2);
  busy_wait_seconds(F2);
  pthread_mutex_unlock(&mu_fill_2);
  return NULL;
}

static void *critical_worker_1(void *arg) {
  (void)arg;
  pthread_mutex_lock(&mu_crit_1);
  busy_wait_seconds(C1);
  pthread_mutex_unlock(&mu_crit_1);
  sem_post(&sem_c12);
  return NULL;
}

static void *critical_worker_2(void *arg) {
  (void)arg;
  sem_wait(&sem_c12);
  pthread_mutex_lock(&mu_crit_2);
  busy_wait_seconds(C2);
  pthread_mutex_unlock(&mu_crit_2);
  sem_post(&sem_c23);
  return NULL;
}

static void *critical_worker_3(void *arg) {
  (void)arg;
  sem_wait(&sem_c23);
  pthread_mutex_lock(&mu_crit_3);
  busy_wait_seconds(C3);
  pthread_mutex_unlock(&mu_crit_3);
  return NULL;
}

int main(void) {
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(0, &cpu_set);
  CPU_SET(1, &cpu_set);
  if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0) {
    fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
  }
  init_matrices();

  if (sem_init(&sem_c12, 0, 0) != 0)
    return 1;
  if (sem_init(&sem_c23, 0, 0) != 0)
    return 1;

  /* 先释放填充任务，再释放关键链入口，让 FIFO 更容易先跑错对象。 */
  pthread_create(&th_fill_1, NULL, fill_worker_1, NULL);
  pthread_create(&th_fill_2, NULL, fill_worker_2, NULL);
  pthread_create(&th_crit_1, NULL, critical_worker_1, NULL);
  pthread_create(&th_crit_2, NULL, critical_worker_2, NULL);
  pthread_create(&th_crit_3, NULL, critical_worker_3, NULL);

  pthread_join(th_fill_1, NULL);
  pthread_join(th_fill_2, NULL);
  pthread_join(th_crit_1, NULL);
  pthread_join(th_crit_2, NULL);
  pthread_join(th_crit_3, NULL);

  pthread_mutex_lock(&mu_tail);
  busy_wait_seconds(TAIL);
  pthread_mutex_unlock(&mu_tail);

  sem_destroy(&sem_c12);
  sem_destroy(&sem_c23);
  return 0;
}
