#pragma once
#include <pthread.h>
#include <sched.h>
#include <string.h>

static inline void l1_set_thread_prio_fifo(int prio) {
    (void)prio;
    int policy = 0;
    struct sched_param sp;
    memset(&sp, 0, sizeof(sp));
    if (pthread_getschedparam(pthread_self(), &policy, &sp) != 0) {
        return;
    }
    (void)pthread_setschedparam(pthread_self(), policy, &sp);
}
