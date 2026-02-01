#define _GNU_SOURCE

#include "segtrace.h"

#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

static __thread uint64_t tls_t0_ns = 0;
static __thread const char *tls_seg = NULL;
static __thread FILE *tls_fp = NULL;
static __thread int tls_inited = 0;

static char g_out_dir[512] = "./trace";
static pthread_once_t g_once = PTHREAD_ONCE_INIT;

static uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

static pid_t get_tid(void) {
    return (pid_t)syscall(SYS_gettid);
}

static void ensure_dir_once(void) {
    // best-effort create dir using POSIX mkdir via system call is overkill here;
    // the Python wrapper will create the directory. Nothing to do.
}

void segtrace_init(const char *out_dir) {
    if (out_dir && out_dir[0]) {
        strncpy(g_out_dir, out_dir, sizeof(g_out_dir) - 1);
        g_out_dir[sizeof(g_out_dir) - 1] = '\0';
    }
}

static void ensure_thread_file(void) {
    if (tls_inited) {
        return;
    }
    pthread_once(&g_once, ensure_dir_once);

    char path[640];
    snprintf(path, sizeof(path), "%s/trace.%d.csv", g_out_dir, (int)get_tid());
    tls_fp = fopen(path, "a");
    if (!tls_fp) {
        // fallback to stderr to avoid crashing
        tls_fp = stderr;
    }
    tls_inited = 1;
}

void segtrace_begin(const char *seg_id) {
    ensure_thread_file();
    // Non-nested assumption: overwrite slot
    tls_seg = seg_id;
    tls_t0_ns = now_ns();
}

void segtrace_end(const char *seg_id) {
    ensure_thread_file();
    uint64_t t1 = now_ns();
    uint64_t dur = (t1 >= tls_t0_ns) ? (t1 - tls_t0_ns) : 0;
    pid_t tid = get_tid();

    // Write: tid, seg_id, begin_ns, end_ns, dur_ns
    // seg_id is quoted to keep CSV robust.
    fprintf(tls_fp, "%d,\"%s\",%llu,%llu,%llu\n",
            (int)tid,
            seg_id ? seg_id : "",
            (unsigned long long)tls_t0_ns,
            (unsigned long long)t1,
            (unsigned long long)dur);
    fflush(tls_fp);

    (void)seg_id; // we don't enforce matching ids in stage1
    tls_seg = NULL;
    tls_t0_ns = 0;
}

