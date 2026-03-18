#define _GNU_SOURCE
#include "prio_runtime.h"
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef WORK_SCALE
#define WORK_SCALE 600
#endif

#define MAT_N 32
static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];

static void init_matrices(void) {
  for (int i = 0; i < MAT_N; ++i) {
    for (int j = 0; j < MAT_N; ++j) {
      mat_a[i][j] = (double)(i + j + 1);
      mat_b[i][j] = (double)(i * 2 + j + 3);
      mat_c[i][j] = 0.0;
    }
  }
}

static void busy_work(int units) {
  for (int r = 0; r < units * WORK_SCALE; ++r) {
    for (int i = 0; i < MAT_N; ++i) {
      for (int j = 0; j < MAT_N; ++j) {
        double accum = 0.0;
        for (int k = 0; k < MAT_N; ++k) {
          accum += mat_a[i][k] * mat_b[k][j];
        }
        mat_c[i][j] = accum;
      }
    }
  }
}

int main(void) {
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(0, &cpu_set);
  sched_setaffinity(0, sizeof(cpu_set), &cpu_set);

  l1_set_thread_prio_fifo(99);
  init_matrices();
  l1_set_thread_prio_fifo(98);
  busy_work(4);
  l1_set_thread_prio_fifo(97);
  busy_work(4);
  l1_set_thread_prio_fifo(96);
  busy_work(4);
  busy_work(4);
  printf("standalone_checksum=%0.3f\n", mat_c[0][0]);
  return 0;
}
