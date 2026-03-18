#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef WORK_SCALE
#define WORK_SCALE 80
#endif

#define MAT_N 64

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];
static volatile double g_sink = 0.0;

static pthread_mutex_t mutex_07 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_02 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_09 = PTHREAD_MUTEX_INITIALIZER;
static sem_t sem_02;

struct helper_args {
  double pre_weight;
  sem_t *sem_ptr;
};

static void init_matrices(void) {
  for (int i = 0; i < MAT_N; ++i) {
    for (int j = 0; j < MAT_N; ++j) {
      mat_a[i][j] = (double)(i + j + 1);
      mat_b[i][j] = (double)(i * 2 + j + 3);
      mat_c[i][j] = 0.0;
    }
  }
}

static void set_affinity_cpu01(void) {
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(0, &cpu_set);
  CPU_SET(1, &cpu_set);
  if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0) {
    fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
  }
}

static uint64_t now_ns(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

static void busy_wait_seconds(double seconds) {
  int repeat_count = (int)(seconds * WORK_SCALE * 0.1);
  if (repeat_count < 1) {
    repeat_count = 1;
  }
  double total = 0.0;
  for (int r = 0; r < repeat_count; ++r) {
    for (int i = 0; i < MAT_N; ++i) {
      for (int j = 0; j < MAT_N; ++j) {
        double accum = 0.0;
        for (int k = 0; k < MAT_N; ++k) {
          accum += mat_a[i][k] * mat_b[k][j];
        }
        mat_c[i][j] = accum;
        total += accum;
      }
    }
  }
  g_sink += total;
}

static void *join_helper(void *arg) {
  struct helper_args *cfg = (struct helper_args *)arg;
  if (cfg->pre_weight > 0.0) {
    busy_wait_seconds(cfg->pre_weight);
  }
  return NULL;
}

static void *sem_helper(void *arg) {
  struct helper_args *cfg = (struct helper_args *)arg;
  if (cfg->pre_weight > 0.0) {
    busy_wait_seconds(cfg->pre_weight);
  }
  sem_post(cfg->sem_ptr);
  return NULL;
}

static uint64_t run_mutex_block(const char *mode, double weight) {
  uint64_t t0 = now_ns();
  pthread_mutex_lock(&mutex_07);
  if (strcmp(mode, "other-only") != 0) {
    busy_wait_seconds(weight);
  }
  pthread_mutex_unlock(&mutex_07);
  return now_ns() - t0;
}

static uint64_t run_sem_block(const char *mode, double weight, double helper_weight) {
  pthread_t helper;
  struct helper_args cfg = {.pre_weight = helper_weight, .sem_ptr = &sem_02};
  sem_destroy(&sem_02);
  sem_init(&sem_02, 0, 0);
  pthread_create(&helper, NULL, sem_helper, &cfg);

  uint64_t t0 = now_ns();
  if (strcmp(mode, "busy-only") == 0) {
    busy_wait_seconds(weight);
  } else {
    pthread_mutex_lock(&mutex_02);
    sem_wait(&sem_02);
    if (strcmp(mode, "other-only") != 0) {
      busy_wait_seconds(weight);
    }
    pthread_mutex_unlock(&mutex_02);
  }
  uint64_t dur = now_ns() - t0;

  pthread_join(helper, NULL);
  return dur;
}

static uint64_t run_join_block(const char *mode, double weight, double helper_weight) {
  pthread_t helper;
  struct helper_args cfg = {.pre_weight = helper_weight, .sem_ptr = NULL};
  pthread_create(&helper, NULL, join_helper, &cfg);

  uint64_t t0 = now_ns();
  if (strcmp(mode, "busy-only") == 0) {
    busy_wait_seconds(weight);
  } else {
    pthread_mutex_lock(&mutex_09);
    pthread_join(helper, NULL);
    if (strcmp(mode, "other-only") != 0) {
      busy_wait_seconds(weight);
    }
    pthread_mutex_unlock(&mutex_09);
  }
  uint64_t dur = now_ns() - t0;

  if (strcmp(mode, "busy-only") == 0) {
    pthread_join(helper, NULL);
  }
  return dur;
}

static int parse_args(int argc, char **argv, const char **block, const char **mode, double *weight,
                      int *repeats, double *helper_weight) {
  if (argc != 6 && argc != 7) {
    fprintf(stderr, "usage: %s <block> <mode> <weight> <repeats> <helper_weight>\n", argv[0]);
    fprintf(stderr, "block=mutex|sem|join mode=other-only|busy-only|full-block\n");
    return 1;
  }
  *block = argv[1];
  *mode = argv[2];
  *weight = atof(argv[3]);
  *repeats = atoi(argv[4]);
  *helper_weight = atof(argv[5]);
  return 0;
}

int main(int argc, char **argv) {
  const char *block = NULL;
  const char *mode = NULL;
  double weight = 0.0;
  int repeats = 0;
  double helper_weight = 0.0;
  if (parse_args(argc, argv, &block, &mode, &weight, &repeats, &helper_weight) != 0) {
    return 1;
  }

  set_affinity_cpu01();
  init_matrices();
  sem_init(&sem_02, 0, 0);

  for (int i = 0; i < repeats; ++i) {
    uint64_t dur = 0;
    if (strcmp(block, "mutex") == 0) {
      dur = run_mutex_block(mode, weight);
    } else if (strcmp(block, "sem") == 0) {
      dur = run_sem_block(mode, weight, helper_weight);
    } else if (strcmp(block, "join") == 0) {
      dur = run_join_block(mode, weight, helper_weight);
    } else {
      fprintf(stderr, "unknown block: %s\n", block);
      return 2;
    }
    printf("%s,%s,%.3f,%d,%.3f,%llu\n", block, mode, weight, i + 1, helper_weight,
           (unsigned long long)dur);
  }

  fprintf(stderr, "SINK=%f\n", g_sink);
  sem_destroy(&sem_02);
  return 0;
}
