#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>

#ifndef ITERATIONS
#define ITERATIONS 200000
#endif

#ifndef USE_PRIO_PROBE
#define USE_PRIO_PROBE 0
#endif

static volatile uint64_t g_sink = 0;

#if USE_PRIO_PROBE
#include "prio_runtime.h"
#endif

static void pin_cpu0(void) {
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(0, &cpu_set);
  sched_setaffinity(0, sizeof(cpu_set), &cpu_set);
}

int main(void) {
  pin_cpu0();
  for (int i = 0; i < ITERATIONS; ++i) {
#if USE_PRIO_PROBE
    l1_set_thread_prio_fifo(99);
#endif
    g_sink += (uint64_t)(i & 7);
  }
  printf("sink=%llu\n", (unsigned long long)g_sink);
  return 0;
}
