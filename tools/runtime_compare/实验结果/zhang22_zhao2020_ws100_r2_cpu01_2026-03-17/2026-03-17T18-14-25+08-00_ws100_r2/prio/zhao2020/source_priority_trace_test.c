#define _GNU_SOURCE
#include "prio_runtime.h"
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define C1 350.0
#define C2 8.0
#define C3 8.0
#define C4 220.0
#define C5 4.0
#define C6 1.0
#define C7 1.0
#define C8 1.0
#define C9 2.0
#define C10 140.0
#define C11 80.0
#define C12 100.0
#define C13 50.0
#define C14 80.0

static void *worker_c0(void *arg);
static void *worker_c1(void *arg);
static void *worker_c2(void *arg);

#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 200
#endif

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];

static pthread_t thread_c0, thread_c1, thread_c2;

static sem_t sem_01;
static sem_t sem_02;
static sem_t sem_03;

static pthread_mutex_t mutex_01 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_02 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_03 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_04 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_05 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_07 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_08 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_09 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_10 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_11 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_12 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_13 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;

static struct timespec prog_start_ts;

static unsigned long long rel_ns(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (unsigned long long)(now.tv_sec - prog_start_ts.tv_sec) * 1000000000ull +
           (unsigned long long)(now.tv_nsec - prog_start_ts.tv_nsec);
}

static const char *policy_name(int policy) {
    switch (policy) {
    case SCHED_FIFO:
        return "FIFO";
    case SCHED_RR:
        return "RR";
    case SCHED_OTHER:
        return "OTHER";
    default:
        return "UNKNOWN";
    }
}

static void trace_log(const char *thread_name, const char *block_name, const char *fmt, ...) {
    int policy = 0;
    struct sched_param sp;
    memset(&sp, 0, sizeof(sp));
    pthread_getschedparam(pthread_self(), &policy, &sp);

    pthread_mutex_lock(&log_lock);
    fprintf(stdout, "[%10llu ns] thread=%-10s block=%-24s policy=%-6s prio=%2d ",
            rel_ns(), thread_name, block_name, policy_name(policy), sp.sched_priority);
    va_list ap;
    va_start(ap, fmt);
    vfprintf(stdout, fmt, ap);
    va_end(ap);
    fputc('\n', stdout);
    fflush(stdout);
    pthread_mutex_unlock(&log_lock);
}

static void set_prio_and_trace(const char *thread_name, const char *block_name, int prio) {
    trace_log(thread_name, block_name, "set-prio-request=%d", prio);
    l1_set_thread_prio_fifo(prio);
    trace_log(thread_name, block_name, "after-set-prio=%d", prio);
}

static void init_matrices(void) {
    for (int i = 0; i < MAT_N; ++i) {
        for (int j = 0; j < MAT_N; ++j) {
            mat_a[i][j] = (double)(i + j + 1);
            mat_b[i][j] = (double)(i * 2 + j + 3);
            mat_c[i][j] = 0.0;
        }
    }
}

static void busy_wait_seconds(double seconds) {
    int repeat_count = (int)(seconds * WORK_SCALE * 0.1);
    if (repeat_count < 1) {
        repeat_count = 1;
    }
    for (int r = 0; r < repeat_count; ++r) {
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

static void run_block(const char *thread_name, const char *block_name, double work_seconds) {
    trace_log(thread_name, block_name, "enter");
    busy_wait_seconds(work_seconds);
    trace_log(thread_name, block_name, "exit");
}

static void *worker_c2(void *arg) {
    (void)arg;

    set_prio_and_trace("worker_c2", "worker_c2#001", 88);
    trace_log("worker_c2", "worker_c2#001", "waiting mutex_01");
    pthread_mutex_lock(&mutex_01);
    trace_log("worker_c2", "worker_c2#001", "acquired mutex_01");
    run_block("worker_c2", "worker_c2#001", C1);
    pthread_mutex_unlock(&mutex_01);
    trace_log("worker_c2", "worker_c2#001", "released mutex_01");

    set_prio_and_trace("worker_c2", "worker_c2#002", 87);
    trace_log("worker_c2", "worker_c2#002", "waiting sem_02");
    pthread_mutex_lock(&mutex_02);
    sem_wait(&sem_02);
    trace_log("worker_c2", "worker_c2#002", "passed sem_02");
    run_block("worker_c2", "worker_c2#002", C2);
    pthread_mutex_unlock(&mutex_02);
    trace_log("worker_c2", "worker_c2#002", "released mutex_02");

    set_prio_and_trace("worker_c2", "worker_c2#003", 86);
    trace_log("worker_c2", "worker_c2#003", "waiting sem_03");
    pthread_mutex_lock(&mutex_03);
    sem_wait(&sem_03);
    trace_log("worker_c2", "worker_c2#003", "passed sem_03");
    run_block("worker_c2", "worker_c2#003", C3);
    pthread_mutex_unlock(&mutex_03);
    trace_log("worker_c2", "worker_c2#003", "released mutex_03");
    return NULL;
}

static void *worker_c1(void *arg) {
    (void)arg;

    set_prio_and_trace("worker_c1", "worker_c1#001", 90);
    trace_log("worker_c1", "worker_c1#001", "waiting mutex_04");
    pthread_mutex_lock(&mutex_04);
    trace_log("worker_c1", "worker_c1#001", "acquired mutex_04");
    run_block("worker_c1", "worker_c1#001", C4);
    pthread_mutex_unlock(&mutex_04);
    trace_log("worker_c1", "worker_c1#001", "released mutex_04");

    set_prio_and_trace("worker_c1", "worker_c1#002", 89);
    trace_log("worker_c1", "worker_c1#002", "waiting sem_01");
    pthread_mutex_lock(&mutex_05);
    sem_wait(&sem_01);
    trace_log("worker_c1", "worker_c1#002", "passed sem_01");
    run_block("worker_c1", "worker_c1#002", C5);
    pthread_mutex_unlock(&mutex_05);
    trace_log("worker_c1", "worker_c1#002", "released mutex_05");
    return NULL;
}

static void *worker_c0(void *arg) {
    (void)arg;

    set_prio_and_trace("worker_c0", "worker_c0#001", 91);
    trace_log("worker_c0", "worker_c0#001", "waiting mutex_07");
    pthread_mutex_lock(&mutex_07);
    trace_log("worker_c0", "worker_c0#001", "acquired mutex_07");
    run_block("worker_c0", "worker_c0#001", C6);
    pthread_mutex_unlock(&mutex_07);
    trace_log("worker_c0", "worker_c0#001", "released mutex_07");
    return NULL;
}

int main(void) {
    clock_gettime(CLOCK_MONOTONIC, &prog_start_ts);
    set_prio_and_trace("main", "main#001", 99);
    trace_log("main", "main#001", "locking mutex_01");
    pthread_mutex_lock(&mutex_01);

    cpu_set_t cpu_set;
    CPU_ZERO(&cpu_set);
    CPU_SET(0, &cpu_set);
    if (sched_setaffinity(0, sizeof(cpu_set), &cpu_set) != 0) {
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
    }

    init_matrices();

    if (sem_init(&sem_01, 0, 0) != 0) {
        return 1;
    }
    if (sem_init(&sem_02, 0, 0) != 0) {
        return 1;
    }
    if (sem_init(&sem_03, 0, 0) != 0) {
        return 1;
    }

    trace_log("main", "main#001", "creating workers");
    pthread_create(&thread_c0, NULL, worker_c0, NULL);
    pthread_create(&thread_c1, NULL, worker_c1, NULL);
    pthread_create(&thread_c2, NULL, worker_c2, NULL);
    run_block("main", "main#001", C7);
    pthread_mutex_unlock(&mutex_01);
    trace_log("main", "main#001", "released mutex_01");

    set_prio_and_trace("main", "main#002", 98);
    trace_log("main", "main#002", "waiting mutex_07");
    pthread_mutex_lock(&mutex_07);
    trace_log("main", "main#002", "acquired mutex_07");
    run_block("main", "main#002", C8);
    pthread_mutex_unlock(&mutex_07);
    trace_log("main", "main#002", "released mutex_07");

    set_prio_and_trace("main", "main#003", 97);
    trace_log("main", "main#003", "waiting mutex_08");
    pthread_mutex_lock(&mutex_08);
    trace_log("main", "main#003", "acquired mutex_08");
    run_block("main", "main#003", C9);
    sem_post(&sem_01);
    trace_log("main", "main#003", "posted sem_01");
    sem_post(&sem_02);
    trace_log("main", "main#003", "posted sem_02");
    pthread_mutex_unlock(&mutex_08);
    trace_log("main", "main#003", "released mutex_08");

    set_prio_and_trace("main", "main#004", 96);
    trace_log("main", "main#004", "waiting mutex_09");
    pthread_mutex_lock(&mutex_09);
    trace_log("main", "main#004", "joining thread_c0");
    pthread_join(thread_c0, NULL);
    trace_log("main", "main#004", "joined thread_c0");
    run_block("main", "main#004", C10);
    pthread_mutex_unlock(&mutex_09);
    trace_log("main", "main#004", "released mutex_09");

    set_prio_and_trace("main", "main#005", 95);
    trace_log("main", "main#005", "waiting mutex_10");
    pthread_mutex_lock(&mutex_10);
    trace_log("main", "main#005", "acquired mutex_10");
    run_block("main", "main#005", C11);
    sem_post(&sem_03);
    trace_log("main", "main#005", "posted sem_03");
    pthread_mutex_unlock(&mutex_10);
    trace_log("main", "main#005", "released mutex_10");

    set_prio_and_trace("main", "main#006", 94);
    trace_log("main", "main#006", "waiting mutex_11");
    pthread_mutex_lock(&mutex_11);
    trace_log("main", "main#006", "joining thread_c1");
    pthread_join(thread_c1, NULL);
    trace_log("main", "main#006", "joined thread_c1");
    run_block("main", "main#006", C12);
    pthread_mutex_unlock(&mutex_11);
    trace_log("main", "main#006", "released mutex_11");

    set_prio_and_trace("main", "main#007", 93);
    trace_log("main", "main#007", "waiting mutex_12");
    pthread_mutex_lock(&mutex_12);
    trace_log("main", "main#007", "acquired mutex_12");
    run_block("main", "main#007", C13);
    pthread_mutex_unlock(&mutex_12);
    trace_log("main", "main#007", "released mutex_12");

    set_prio_and_trace("main", "main#008", 92);
    trace_log("main", "main#008", "waiting mutex_13");
    pthread_mutex_lock(&mutex_13);
    trace_log("main", "main#008", "joining thread_c2");
    pthread_join(thread_c2, NULL);
    trace_log("main", "main#008", "joined thread_c2");
    run_block("main", "main#008", C14);
    pthread_mutex_unlock(&mutex_13);
    trace_log("main", "main#008", "released mutex_13");
    return 0;
}
