#define _GNU_SOURCE
#include "time_stat.h"
#include <time.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef struct {
    char key[160];
    unsigned long long total_ns;
    unsigned long long count;
    unsigned long long max_ns;
    unsigned long long min_ns;
} stat_item;

static stat_item *g_stats = NULL;
static size_t g_cap = 0, g_sz = 0;
static pthread_mutex_t g_mu = PTHREAD_MUTEX_INITIALIZER;
static int g_dumped = 0;
static FILE *g_trace_fp = NULL;
static int g_trace_first = 1;

static void ensure_cap(void) {
    if (g_sz < g_cap) return;
    size_t nc = g_cap ? g_cap * 2 : 256;
    stat_item *np = (stat_item*)realloc(g_stats, nc * sizeof(stat_item));
    if (!np) exit(2);
    for (size_t i = g_cap; i < nc; ++i) {
        np[i].key[0] = 0;
        np[i].total_ns = np[i].count = np[i].max_ns = 0;
        np[i].min_ns = ~0ull;
    }
    g_stats = np; g_cap = nc;
}

uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

static stat_item* get_slot(const char* key) {
    for (size_t i = 0; i < g_sz; ++i) {
        if (strcmp(g_stats[i].key, key) == 0) return &g_stats[i];
    }
    ensure_cap();
    strncpy(g_stats[g_sz].key, key, sizeof(g_stats[g_sz].key) - 1);
    g_stats[g_sz].key[sizeof(g_stats[g_sz].key) - 1] = 0;
    g_stats[g_sz].total_ns = 0;
    g_stats[g_sz].count = 0;
    g_stats[g_sz].max_ns = 0;
    g_stats[g_sz].min_ns = ~0ull;
    return &g_stats[g_sz++];
}

static void trace_init_locked(void) {
    if (g_trace_fp) return;
    g_trace_fp = fopen("thread_trace.json", "w");
    if (!g_trace_fp) return;
    fputs("[\n", g_trace_fp);
    g_trace_first = 1;
}

void time_trace(const char* key, uint64_t start_ns, uint64_t dur_ns) {
    pthread_mutex_lock(&g_mu);
    trace_init_locked();
    if (g_trace_fp) {
        if (!g_trace_first) fputs(",\n", g_trace_fp);
        g_trace_first = 0;
        fprintf(
            g_trace_fp, "  {\"key\": \"%s\", \"start_ns\": %llu, \"dur_ns\": %llu}",
            key,
            (unsigned long long)start_ns,
            (unsigned long long)dur_ns
        );
    }
    pthread_mutex_unlock(&g_mu);
}

void time_account(const char* key, uint64_t dur_ns) {
    pthread_mutex_lock(&g_mu);
    stat_item* s = get_slot(key);
    s->total_ns += dur_ns;
    s->count += 1;
    if (dur_ns > s->max_ns) s->max_ns = dur_ns;
    if (dur_ns < s->min_ns) s->min_ns = dur_ns;
    pthread_mutex_unlock(&g_mu);
}

static void dump_json_locked(void) {
    if (g_dumped) return;
    g_dumped = 1;
    FILE *fp = fopen("time_result.json", "w");
    if (!fp) return;
    fprintf(fp, "{\n");
    for (size_t i = 0; i < g_sz; ++i) {
        unsigned long long avg = g_stats[i].count ? (g_stats[i].total_ns / g_stats[i].count) : 0ull;
        fprintf(fp,
            "  \"%s\": {\"total_ns\": %llu, \"count\": %llu, \"avg_ns\": %llu, \"max_ns\": %llu, \"min_ns\": %llu}%s\n",
            g_stats[i].key,
            g_stats[i].total_ns,
            g_stats[i].count,
            avg,
            g_stats[i].max_ns,
            (g_stats[i].min_ns == ~0ull ? 0ull : g_stats[i].min_ns),
            (i + 1 == g_sz) ? "" : ","
        );
    }
    fprintf(fp, "}\n");
    fclose(fp);
}

static void dump_trace_locked(void) {
    if (!g_trace_fp) return;
    fputs("\n]\n", g_trace_fp);
    fclose(g_trace_fp);
    g_trace_fp = NULL;
}

__attribute__((destructor))
static void at_exit_dump(void) {
    pthread_mutex_lock(&g_mu);
    dump_json_locked();
    dump_trace_locked();
    pthread_mutex_unlock(&g_mu);
}
