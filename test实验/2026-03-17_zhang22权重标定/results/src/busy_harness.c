#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>

#ifndef WORK_SCALE
#define WORK_SCALE 1000
#endif

#ifndef BUSY_WEIGHT
#define BUSY_WEIGHT 1.0
#endif

#ifndef BUSY_REPEATS
#define BUSY_REPEATS 1
#endif

static volatile double g_busy_sink = 0.0;

static void pin_cpu0(void) {
  cpu_set_t cpu_set;
  CPU_ZERO(&cpu_set);
  CPU_SET(0, &cpu_set);
  sched_setaffinity(0, sizeof(cpu_set), &cpu_set);
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
}

int main(void) {
  pin_cpu0();
  for (int i = 0; i < BUSY_REPEATS; ++i) {
    busy_wait_seconds(BUSY_WEIGHT);
  }
  printf("busy_sink=%0.6f\n", g_busy_sink);
  return 0;
}
