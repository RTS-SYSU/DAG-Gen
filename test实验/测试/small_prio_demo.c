#define _GNU_SOURCE
#include "prio_runtime.h"
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>

#ifndef WORK_SCALE
#define WORK_SCALE 120000
#endif

static volatile long long g_busy_sink = 0;
static volatile int g_sequence = 0;

// ================== 可修改的优先级变量（重点） ==================
static int prio_t1 = 90;   // T1 优先级
static int prio_t2 = 30;   // T2 优先级  
static int prio_t3 = 60;   // T3 优先级 (最高)
// ============================================================

static void busy_wait_seconds(double seconds) {
    long long iterations = (long long)(seconds * WORK_SCALE * 800LL);
    volatile long long acc = 0;
    for (long long i = 0; i < iterations; ++i) {
        acc += i % 137;
        if (i % 80000 == 0) {
            acc ^= (i & 0xFF);
        }
    }
    g_busy_sink += acc;
}

static void print_with_seq(const char* name, const char* msg, int prio) {
    int seq = __sync_fetch_and_add(&g_sequence, 1);
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    double t = ts.tv_sec + ts.tv_nsec / 1000000000.0;
    printf("[%6.3f][%02d] %s (prio=%2d): %s\n", t, seq, name, prio, msg);
}

static void *thread1_fn(void *arg) {
    l1_set_thread_prio_fifo(prio_t1);
    print_with_seq("T1", "启动", prio_t1);
    
    busy_wait_seconds(2.2);
    print_with_seq("T1", "第一阶段完成", prio_t1);
    
    busy_wait_seconds(1.3);
    print_with_seq("T1", "全部完成", prio_t1);
    return NULL;
}

static void *thread2_fn(void *arg) {
    l1_set_thread_prio_fifo(prio_t2);
    print_with_seq("T2", "启动", prio_t2);
    
    busy_wait_seconds(1.8);
    print_with_seq("T2", "完成", prio_t2);
    return NULL;
}

static void *thread3_fn(void *arg) {
    l1_set_thread_prio_fifo(prio_t3);
    print_with_seq("T3", "启动", prio_t3);
    
    busy_wait_seconds(1.1);
    print_with_seq("T3", "完成", prio_t3);
    return NULL;
}

int main(void) {
    pthread_t t1, t2, t3;
    struct timespec ts_start, ts_end;
    cpu_set_t set;
    int cpu;
    
    printf("=== 优先级抢占演示 DEMO (单核) ===\n");
    printf("优先级设置: T1=%d, T2=%d, T3=%d\n\n", prio_t1, prio_t2, prio_t3);
    
    // 确认绑定到哪个核心
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    if (sched_setaffinity(0, sizeof(set), &set) == 0) {
        cpu = sched_getcpu();
        printf("已绑定到 CPU %d\n", cpu);
    } else {
        printf("绑定CPU失败\n");
    }
    
    clock_gettime(CLOCK_MONOTONIC, &ts_start);
    
    // 创建顺序：T1 -> T2 -> T3
    pthread_create(&t1, NULL, thread1_fn, NULL);
    pthread_create(&t2, NULL, thread2_fn, NULL);
    pthread_create(&t3, NULL, thread3_fn, NULL);
    
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    pthread_join(t3, NULL);
    
    clock_gettime(CLOCK_MONOTONIC, &ts_end);
    double elapsed = (ts_end.tv_sec - ts_start.tv_sec) + 
                     (ts_end.tv_nsec - ts_start.tv_nsec) / 1000000000.0;
    
    printf("\n=== 最终结果 ===\n");
    printf("总运行时间: %.2f 秒\n", elapsed);
    printf("g_sequence = %d\n\n", g_sequence);
    
    printf("验证说明：\n");
    printf("1. 虽然绑定在单核，但高优先级线程会优先获得CPU\n");
    printf("2. 把 prio_t1 改成 95 再跑，对比执行顺序变化\n");
    printf("3. 把 prio_t3 改成 20 再跑，观察 T3 是否被延后\n");
    printf("4. 重点看 [时间][序号] 这一列的顺序\n");
    
    return 0;
}
