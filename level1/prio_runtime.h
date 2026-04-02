#pragma once

#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>

static inline void l1_set_thread_prio_fifo(int prio) {
    struct sched_param sp;
    memset(&sp, 0, sizeof(sp));
    sp.sched_priority = prio;
    // Best-effort: ignore EPERM when not running with CAP_SYS_NICE/root.
    int rc = pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);
    if (rc != 0) {
        fprintf(stderr, "L1_PRIO_SET_FAILED rc=%d errno=%d (%s)\n", rc, errno, strerror(errno));
        fprintf(stderr, "ERROR: 需要 root/sudo 权限才能设置实时优先级！请使用 sudo 运行。\n");
    }
}
