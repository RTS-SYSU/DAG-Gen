// 多核调度基准示例：调整 core_policy 控制核心分配规则，便于用 mycallyplus 做插桩与时延对比
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>

// -------- 配置区 --------
// 0: 全部线程绑定 core0
// 1: 线程均匀分布 core0/1/2/3（按序循环）
// 2: 自定义映射（core_map_custom）
static int core_policy = 1;
static int core_map_custom[] = {0, 2, 3, 1}; // 根据需要调整
// 每个线程的工作量（迭代次数，越大越耗时）
static const int work_iters = 80 * 1000 * 1000;
// ------------------------

#define THREAD_N 4

typedef struct {
    int tid;
    int core;
    uint64_t duration_ns;
} task_arg_t;

static uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

static void bind_core(int core) {
    if (core < 0)
        return;
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
}

static void busy_work(int tid, int iters) {
    // 简单算术与访存混合，避免编译器优化掉
    volatile uint64_t acc = (uint64_t)(tid + 1);
    for (int i = 0; i < iters; ++i) {
        acc += (i ^ tid) * 1664525u + 1013904223u;
        acc ^= acc >> 13;
    }
    if (acc == 0x1234) {
        printf("acc guard: %lu\n", acc);
    }
}

static void *worker(void *arg) {
    task_arg_t *ctx = (task_arg_t *)arg;
    bind_core(ctx->core);
    uint64_t t0 = now_ns();
    busy_work(ctx->tid, work_iters);
    busy_work(ctx->tid, work_iters / 4);
    uint64_t t1 = now_ns();
    ctx->duration_ns = t1 - t0;
    return NULL;
}

static int pick_core(int idx) {
    if (core_policy == 0) return 0;
    if (core_policy == 1) return idx % sysconf(_SC_NPROCESSORS_ONLN);
    int sz = (int)(sizeof(core_map_custom) / sizeof(core_map_custom[0]));
    return core_map_custom[idx % sz];
}

int main(void) {
    pthread_t th[THREAD_N];
    task_arg_t args[THREAD_N];

    for (int i = 0; i < THREAD_N; ++i) {
        args[i].tid = i;
        args[i].core = pick_core(i);
        args[i].duration_ns = 0;
        if (pthread_create(&th[i], NULL, worker, &args[i]) != 0) {
            perror("pthread_create");
            return 1;
        }
    }

    for (int i = 0; i < THREAD_N; ++i) {
        pthread_join(th[i], NULL);
    }

    printf("core_policy=%d\n", core_policy);
    for (int i = 0; i < THREAD_N; ++i) {
        printf("thread%02d core=%d\n", args[i].tid, args[i].core);
    }

    return 0;
}
