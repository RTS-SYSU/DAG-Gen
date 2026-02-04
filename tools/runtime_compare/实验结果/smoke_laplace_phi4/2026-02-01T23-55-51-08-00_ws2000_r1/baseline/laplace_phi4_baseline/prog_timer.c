#define _GNU_SOURCE

#include "prog_timer.h"

#include <inttypes.h>
#include <stdio.h>
#include <time.h>

static struct timespec g_begin;
static struct timespec g_end;
static uint64_t g_total_ns = 0;

static uint64_t diff_ns(struct timespec a, struct timespec b)
{
    uint64_t sa = (uint64_t)a.tv_sec * 1000000000ULL + (uint64_t)a.tv_nsec;
    uint64_t sb = (uint64_t)b.tv_sec * 1000000000ULL + (uint64_t)b.tv_nsec;
    return (sb >= sa) ? (sb - sa) : 0;
}

void l1_prog_begin(void)
{
    clock_gettime(CLOCK_MONOTONIC, &g_begin);
}

void l1_prog_end(void)
{
    clock_gettime(CLOCK_MONOTONIC, &g_end);
    g_total_ns = diff_ns(g_begin, g_end);
    fprintf(stderr, "PROGRAM_TOTAL_NS=%" PRIu64 "\n", g_total_ns);
}

uint64_t l1_prog_total_ns(void)
{
    return g_total_ns;
}

