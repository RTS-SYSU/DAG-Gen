#define _GNU_SOURCE
#include "prio_runtime.h"
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static pthread_t thread_a;
static pthread_t thread_b;
static sem_t sem_start_b;
static pthread_mutex_t log_lock = PTHREAD_MUTEX_INITIALIZER;
static struct timespec start_ts;

static unsigned long long rel_ns(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    return (unsigned long long)(now.tv_sec - start_ts.tv_sec) * 1000000000ull +
           (unsigned long long)(now.tv_nsec - start_ts.tv_nsec);
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

static void log_event(const char *thread_name, const char *phase, const char *fmt, ...) {
    int policy = 0;
    struct sched_param sp;
    va_list ap;

    memset(&sp, 0, sizeof(sp));
    pthread_getschedparam(pthread_self(), &policy, &sp);

    pthread_mutex_lock(&log_lock);
    fprintf(stdout, "[%10llu ns] thread=%-5s policy=%-6s prio=%2d phase=%-18s ",
            rel_ns(), thread_name, policy_name(policy), sp.sched_priority, phase);
    va_start(ap, fmt);
    vfprintf(stdout, fmt, ap);
    va_end(ap);
    fputc('\n', stdout);
    fflush(stdout);
    pthread_mutex_unlock(&log_lock);
}

static void burn_cpu(unsigned long outer_loops) {
    volatile unsigned long x = 0;
    for (unsigned long i = 0; i < outer_loops; ++i) {
        for (unsigned long j = 0; j < 500000UL; ++j) {
            x += i + j;
        }
    }
    (void)x;
}

static void bind_to_cpu0(void) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0) {
        fprintf(stderr, "sched_setaffinity failed: %s\n", strerror(errno));
    }
}

static void *worker_b(void *arg) {
    (void)arg;
    bind_to_cpu0();
    log_event("B", "boot", "request prio=80");
    l1_set_thread_prio_fifo(80);
    log_event("B", "boot", "after prio set");
    log_event("B", "wait", "waiting sem_start_b");
    sem_wait(&sem_start_b);
    log_event("B", "ready", "woken and runnable");
    log_event("B", "run", "start block B1");
    burn_cpu(12);
    log_event("B", "run", "end block B1");
    return NULL;
}

static void *worker_a(void *arg) {
    (void)arg;
    bind_to_cpu0();
    log_event("A", "boot", "request prio=90");
    l1_set_thread_prio_fifo(90);
    log_event("A", "boot", "after prio set");
    log_event("A", "block_A1", "start");
    burn_cpu(8);
    log_event("A", "block_A1", "end");

    log_event("A", "drop", "request prio=70");
    l1_set_thread_prio_fifo(70);
    log_event("A", "drop", "after prio set, about to wake B");
    sem_post(&sem_start_b);
    log_event("A", "drop", "returned from sem_post");

    log_event("A", "block_A2", "start");
    burn_cpu(8);
    log_event("A", "block_A2", "end");
    return NULL;
}

int main(void) {
    clock_gettime(CLOCK_MONOTONIC, &start_ts);
    bind_to_cpu0();

    if (sem_init(&sem_start_b, 0, 0) != 0) {
        perror("sem_init");
        return 1;
    }

    log_event("main", "boot", "request prio=60");
    l1_set_thread_prio_fifo(60);
    log_event("main", "boot", "after prio set");

    pthread_create(&thread_b, NULL, worker_b, NULL);
    pthread_create(&thread_a, NULL, worker_a, NULL);

    pthread_join(thread_a, NULL);
    pthread_join(thread_b, NULL);
    log_event("main", "done", "joined A and B");
    return 0;
}
