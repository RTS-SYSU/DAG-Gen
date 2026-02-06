#define _GNU_SOURCE

#include "prog_timer.h"

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static uint64_t g_t0 = 0;
static int g_registered = 0;

static uint64_t now_ns(void) {
    struct timespec ts;
#ifdef CLOCK_MONOTONIC_RAW
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
#else
    clock_gettime(CLOCK_MONOTONIC, &ts);
#endif
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

void l1_prog_begin(void) {
    g_t0 = now_ns();
    if (!g_registered) {
        atexit(l1_prog_end);
        g_registered = 1;
    }
}

void l1_prog_end(void) {
    uint64_t t1 = now_ns();
    uint64_t dur = (t1 >= g_t0) ? (t1 - g_t0) : 0;
    fprintf(stderr, "PROGRAM_TOTAL_NS=%llu\n", (unsigned long long)dur);
    fflush(stderr);
}
