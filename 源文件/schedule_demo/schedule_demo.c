// 多核调度基准示例：调整 core_policy 控制核心分配规则，便于用 mycallyplus 做插桩与时延对比
#define _GNU_SOURCE
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>

// -------- 配置区 --------
// 0: 全部线程绑定 core0
// 1: 线程均匀分布 core0/1/2/3/...（按序循环）
// 2: 自定义映射（core_map_custom）
static int core_policy = 1;
static int core_map_custom[] = {0, 2, 3, 1}; // 根据需要调整
// 每个线程的工作量（迭代次数，越大越耗时）
static const int work_iters = 80 * 1000 * 1000;
// ------------------------

#define THREAD_N 5

// forward decl
static int pick_core(int idx);

// 线程句柄设置为全局变量，便于外部/后续扩展使用
static pthread_t th0, th1, th2, th3, th4;

static void bind_core(int core) {
    if (core < 0)
        return;
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(core, &cpuset);
    pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
}

// ---------- 负载函数（用于制造较丰富的调用图） ----------
static uint64_t mix64(uint64_t x) {
    x ^= x >> 33;
    x *= 0xff51afd7ed558ccdULL;
    x ^= x >> 33;
    x *= 0xc4ceb9fe1a85ec53ULL;
    x ^= x >> 33;
    return x;
}

static void compute_loop(int iters, uint64_t seed) {
    volatile uint64_t acc = seed;
    for (int i = 0; i < iters; ++i) {
        acc = mix64(acc + (uint64_t)i);
    }
    if (acc == 0x1234) printf("guard %lu\n", (unsigned long)acc);
}

static void memory_walk(int iters) {
    const int n = 1024 * 64;
    uint32_t *buf = (uint32_t *)malloc((size_t)n * sizeof(uint32_t));
    if (!buf) return;
    for (int i = 0; i < n; ++i) buf[i] = (uint32_t)i;
    volatile uint32_t sum = 0;
    for (int i = 0; i < iters; ++i) {
        sum += buf[(i * 13) & (n - 1)];
    }
    if (sum == 0xdead) printf("sum %u\n", sum);
    free(buf);
}

static int gcd_int(int a, int b) {
    while (b != 0) {
        int t = a % b;
        a = b;
        b = t;
    }
    return a;
}

static void small_math(int iters) {
    volatile int g = 1;
    for (int i = 1; i < iters; ++i) {
        g = gcd_int(g + i, i | 1);
    }
    if (g == 0x777) printf("g %d\n", g);
}

static void sort_tiny(int iters) {
    const int m = 64;
    int a[m];
    for (int i = 0; i < m; ++i) a[i] = (m - i) ^ iters;
    for (int r = 0; r < m; ++r) {
        for (int i = 1; i < m; ++i) {
            if (a[i] < a[i - 1]) {
                int t = a[i]; a[i] = a[i - 1]; a[i - 1] = t;
            }
        }
    }
    if (a[0] == 0x555) printf("a0 %d\n", a[0]);
}

static void io_sim(int iters) {
    // 很短的 sleep + 计算混合，模拟 IO 等待
    for (int i = 0; i < iters; ++i) {
        if ((i & 0x3fffff) == 0) usleep(10);
    }
}
// ---------------------------------------------------

static void *worker_a(void *arg) {
    (void)arg;
    bind_core(pick_core(0));
    compute_loop(work_iters / 2, 0x1111);
    memory_walk(work_iters / 8);
    small_math(work_iters / 32);
    return NULL;
}

static void *worker_b(void *arg) {
    (void)arg;
    bind_core(pick_core(1));
    memory_walk(work_iters / 6);
    compute_loop(work_iters / 3, 0x2222);
    sort_tiny(1);
    return NULL;
}

static void *worker_c(void *arg) {
    (void)arg;
    bind_core(pick_core(2));
    small_math(work_iters / 24);
    compute_loop(work_iters / 2, 0x3333);
    io_sim(work_iters / 16);
    return NULL;
}

static void *worker_d(void *arg) {
    (void)arg;
    bind_core(pick_core(3));
    compute_loop(work_iters / 4, 0x4444);
    sort_tiny(2);
    memory_walk(work_iters / 10);
    return NULL;
}

static void *worker_e(void *arg) {
    (void)arg;
    bind_core(pick_core(4));
    io_sim(work_iters / 8);
    small_math(work_iters / 28);
    compute_loop(work_iters / 5, 0x5555);
    return NULL;
}

static int pick_core(int idx) {
    if (core_policy == 0) return 0;
    if (core_policy == 1) return idx % sysconf(_SC_NPROCESSORS_ONLN);
    int sz = (int)(sizeof(core_map_custom) / sizeof(core_map_custom[0]));
    return core_map_custom[idx % sz];
}

int main(void) {
    if (pthread_create(&th0, NULL, worker_a, NULL) != 0) { perror("pthread_create a"); return 1; }
    if (pthread_create(&th1, NULL, worker_b, NULL) != 0) { perror("pthread_create b"); return 1; }
    if (pthread_create(&th2, NULL, worker_c, NULL) != 0) { perror("pthread_create c"); return 1; }
    if (pthread_create(&th3, NULL, worker_d, NULL) != 0) { perror("pthread_create d"); return 1; }
    if (pthread_create(&th4, NULL, worker_e, NULL) != 0) { perror("pthread_create e"); return 1; }

    pthread_join(th0, NULL);
    pthread_join(th1, NULL);
    pthread_join(th2, NULL);
    pthread_join(th3, NULL);
    pthread_join(th4, NULL);

    printf("core_policy=%d\n", core_policy);
    printf("thread_a core=%d\n", pick_core(0));
    printf("thread_b core=%d\n", pick_core(1));
    printf("thread_c core=%d\n", pick_core(2));
    printf("thread_d core=%d\n", pick_core(3));
    printf("thread_e core=%d\n", pick_core(4));

    return 0;
}
