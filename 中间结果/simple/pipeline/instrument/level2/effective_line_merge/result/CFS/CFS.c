/*
 * simple.c — 约定文档 +「先算规模再忙等」
 *
 * busy_wait_seconds 使用宏（与 zhang9 一致），源码里仍可见 busy_wait_seconds(Cn) 供 timing 识别；
 * 规模由函数 compute_work_scale 计算，RTL/DAG 中保留 busy_wait_seconds → compute_work_scale 的调用关系
 * （宏体会内联出对 compute_work_scale 的调用）。
 *
 * Pipeline：
 *   cd .../ScratchDAG && PYTHONPATH=.. python3 -m ScratchDAG pipeline run_all \
 *     --source 源文件/simple/simple.c --base-name simple
 */

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

#define C1 1.0
#define C2 2.0
#define C3 3.0
#define C4 4.0
#define C5 5.0

static pthread_mutex_t mutex_01 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_02 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_03 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_04 = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_05 = PTHREAD_MUTEX_INITIALIZER;

static pthread_t thread_01;

static unsigned compute_work_scale(double seconds) {
    int units = (int)(seconds * WORK_SCALE + 0.5);
    if (units < 1) {
        units = 1;
    }
    unsigned w = (unsigned)units * 1000u;
    unsigned s = w * 3u + 17u;
    s ^= (s << 3);
    return s + (w >> 1);
}

#define busy_wait_seconds(seconds)                                          \
    do {                                                                    \
        unsigned _bw_n = compute_work_scale(seconds);                         \
        volatile unsigned long long _bw_spin = 0;                           \
        for (unsigned _bw_i = 0; _bw_i < _bw_n; ++_bw_i) {                 \
            _bw_spin += (unsigned long long)_bw_i;                         \
        }                                                                   \
        (void)_bw_spin;                                                     \
    } while (0)

static void *worker_main(void *arg) {
    pthread_mutex_lock(&mutex_03);
    busy_wait_seconds(C3);
    pthread_mutex_unlock(&mutex_03);

    pthread_mutex_lock(&mutex_04);
    busy_wait_seconds(C4);
    pthread_mutex_unlock(&mutex_04);

    return NULL;
}

int main(void) {
    int *payload = malloc(sizeof(int));
    if (!payload) {
        return 1;
    }
    *payload = 0;

    pthread_mutex_lock(&mutex_01);
    busy_wait_seconds(C1);
    pthread_mutex_unlock(&mutex_01);

    if (pthread_create(&thread_01, NULL, worker_main, payload) != 0) {
        free(payload);
        return 1;
    }

    pthread_mutex_lock(&mutex_02);
    busy_wait_seconds(C2);
    pthread_mutex_unlock(&mutex_02);

    pthread_join(thread_01, NULL);

    pthread_mutex_lock(&mutex_05);
    busy_wait_seconds(C5);
    pthread_mutex_unlock(&mutex_05);

    free(payload);
    return 0;
}
