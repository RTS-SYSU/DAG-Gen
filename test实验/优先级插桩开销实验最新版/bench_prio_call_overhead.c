#define _GNU_SOURCE

#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "../../level1/prio_runtime.h"

#ifndef MEASURE_COUNT
#define MEASURE_COUNT 101
#endif

#ifndef WARMUP_COUNT
#define WARMUP_COUNT 0
#endif

#ifndef OUTPUT_PATH
#define OUTPUT_PATH "prio_call_overhead_results.csv"
#endif

static uint64_t timespec_to_ns(const struct timespec *ts) {
    return (uint64_t)ts->tv_sec * 1000000000ull + (uint64_t)ts->tv_nsec;
}

static uint64_t diff_ns(const struct timespec *t0, const struct timespec *t1) {
    return timespec_to_ns(t1) - timespec_to_ns(t0);
}

static void pin_cpu0(void) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0) {
        perror("sched_setaffinity");
    }
}

int main(void) {
    struct timespec t0;
    struct timespec t1;
    uint64_t samples[MEASURE_COUNT];
    uint64_t sum_ns = 0;
    uint64_t min_ns = UINT64_MAX;
    uint64_t max_ns = 0;
    FILE *fp = NULL;

    pin_cpu0();

    for (int i = 0; i < WARMUP_COUNT; ++i) {
        l1_set_thread_prio_fifo(76);
    }

    for (int i = 0; i < MEASURE_COUNT; ++i) {
        if (clock_gettime(CLOCK_MONOTONIC_RAW, &t0) != 0) {
            perror("clock_gettime start");
            return 1;
        }

        l1_set_thread_prio_fifo(76);

        if (clock_gettime(CLOCK_MONOTONIC_RAW, &t1) != 0) {
            perror("clock_gettime end");
            return 1;
        }

        samples[i] = diff_ns(&t0, &t1);
    }

    for (int i = 1; i < MEASURE_COUNT; ++i) {
        sum_ns += samples[i];
        if (samples[i] < min_ns) {
            min_ns = samples[i];
        }
        if (samples[i] > max_ns) {
            max_ns = samples[i];
        }
    }

    fp = fopen(OUTPUT_PATH, "w");
    if (fp == NULL) {
        perror("fopen output");
        return 1;
    }

    fprintf(fp, "index,sample_value,sample_unit,used_for_stats\n");
    for (int i = 0; i < MEASURE_COUNT; ++i) {
        fprintf(fp, "%d,%llu,ns,%s\n",
                i,
                (unsigned long long)samples[i],
                i == 0 ? "no" : "yes");
    }
    fprintf(fp, "summary,avg,%.2f,ns\n", (double)sum_ns / (double)(MEASURE_COUNT - 1));
    fprintf(fp, "summary,min,%llu,ns\n", (unsigned long long)min_ns);
    fprintf(fp, "summary,max,%llu,ns\n", (unsigned long long)max_ns);
    fclose(fp);

    printf("measure_count=%d\n", MEASURE_COUNT);
    printf("warmup_count=%d\n", WARMUP_COUNT);
    printf("clock=CLOCK_MONOTONIC_RAW\n");
    printf("time_unit=ns\n");
    printf("target_call=l1_set_thread_prio_fifo(76)\n");
    printf("discarded_index=0\n");
    printf("output_path=%s\n", OUTPUT_PATH);
    printf("samples(ns):\n");
    for (int i = 0; i < MEASURE_COUNT; ++i) {
        printf("  [%03d] %llu%s\n",
               i,
               (unsigned long long)samples[i],
               i == 0 ? "  <- discarded from stats" : "");
    }
    printf("stats_count=%d\n", MEASURE_COUNT - 1);
    printf("avg=%.2f ns\n", (double)sum_ns / (double)(MEASURE_COUNT - 1));
    printf("min=%llu ns\n", (unsigned long long)min_ns);
    printf("max=%llu ns\n", (unsigned long long)max_ns);
    return 0;
}
