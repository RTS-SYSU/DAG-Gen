#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <iostream>

// -----------------------------------------------------------------------------
// 简化版任务实现：使用 C 风格指针传参与解引用，避免 unique_ptr/auto/static_cast 等。
// -----------------------------------------------------------------------------
static void simulate_work(const char *name, int value)
{
    std::cout << "[task] " << name << " arg=" << value << std::endl;
    volatile int acc = 0;
    for (int i = 0; i < 10000; ++i) {
        acc += (value + i) % 7;
    }
    (void)acc;
}

static int arg_to_int(void *arg)
{
    if (!arg) return 0;
    return *((int *)arg); // C 风格转换 + 解引用
}

void Deg2rad(void *arg)    { simulate_work("Deg2rad",   arg_to_int(arg)); }
void rad2deg(void *arg)    { simulate_work("rad2deg",    arg_to_int(arg)); }
void cover(void *arg)      { simulate_work("cover",      arg_to_int(arg)); }
void duff(void *arg)       { simulate_work("duff",       arg_to_int(arg)); }
void insertsort(void *arg) { simulate_work("insertsort", arg_to_int(arg)); }
void minver(void *arg)     { simulate_work("minver",     arg_to_int(arg)); }
void ndes(void *arg)       { simulate_work("ndes",       arg_to_int(arg)); }
void ludcmp(void *arg)     { simulate_work("ludcmp",     arg_to_int(arg)); }
void prime(void *arg)      { simulate_work("prime",      arg_to_int(arg)); }

// -----------------------------------------------------------------------------
// 线程层次结构：
//   main -> threadTask1 -> threadTask2 -> {threadTask3, threadTask4}
// -----------------------------------------------------------------------------
static pthread_t g_thread_lvl0 {};
static pthread_t g_thread_lvl1 {};
static pthread_t g_thread_lvl2 {};
static pthread_t g_thread_lvl3 {};

void *threadTask3(void *arg)
{
    int *payload = (int *)arg; // C 风格转换
    rad2deg(payload);
    std::cout << "task8 完成" << std::endl;
    if (payload) free(payload); // 在线程内释放自己拥有的参数
    return NULL;
}

void *threadTask4(void *arg)
{
    int *payload = (int *)arg;
    prime(payload);
    std::cout << "task9 完成" << std::endl;
    if (payload) free(payload);
    return NULL;
}

void *threadTask2(void *arg)
{
    int *root = (int *)arg;

    // 为子线程准备参数（使用 malloc 分配，子线程内释放）
    int *task_arg1 = (int *)malloc(sizeof(int));
    int *task_arg2 = (int *)malloc(sizeof(int));
    if (task_arg1) *task_arg1 = 43;
    if (task_arg2) *task_arg2 = 44;

    minver(root);
    std::cout << "task5 完成" << std::endl;

    if (pthread_create(&g_thread_lvl2, NULL, threadTask3, task_arg1) != 0) {
        std::perror("pthread_create threadTask3 failed");
        if (task_arg1) free(task_arg1);
        if (task_arg2) free(task_arg2);
        if (root) free(root);
        return NULL;
    }

    if (pthread_create(&g_thread_lvl3, NULL, threadTask4, task_arg2) != 0) {
        std::perror("pthread_create threadTask4 failed");
        // 回收前一个已创建线程
        pthread_join(g_thread_lvl2, NULL);
        if (task_arg2) free(task_arg2);
        if (root) free(root);
        return NULL;
    }

    ndes(root);
    std::cout << "task6 完成" << std::endl;

    pthread_join(g_thread_lvl2, NULL);
    pthread_join(g_thread_lvl3, NULL);

    ludcmp(root);
    std::cout << "task7 完成" << std::endl;

    if (root) free(root);
    return NULL;
}

void *threadTask1(void *arg)
{
    int *root = (int *)arg;

    // 为下一级线程准备参数
    int *nested_arg = (int *)malloc(sizeof(int));
    if (nested_arg) *nested_arg = 42;

    Deg2rad(root);
    std::cout << "task1 完成" << std::endl;

    if (pthread_create(&g_thread_lvl1, NULL, threadTask2, nested_arg) != 0) {
        std::perror("pthread_create threadTask2 failed");
        if (nested_arg) free(nested_arg);
        if (root) free(root);
        return NULL;
    }

    cover(root);
    std::cout << "task2 完成" << std::endl;

    duff(root);
    std::cout << "task3 完成" << std::endl;

    pthread_join(g_thread_lvl1, NULL);

    insertsort(root);
    std::cout << "task4 完成" << std::endl;

    if (root) free(root);
    return NULL;
}

void threadTask5()
{
    int i = 0;
    while (i < 3) {
        std::cout << "while 测试: i=" << i << std::endl;
        ++i;
    }

    do {
        std::cout << "do-while 测试" << std::endl;
        --i;
    } while (i == 0);

    for (int j = 0; j < 5; ++j) {
        std::cout << "for 测试 j=" << j << std::endl;
    }

    int j = 2;
    switch (j) {
    case 1:
        std::cout << "switch:1" << std::endl;
        break;
    case 2:
        std::cout << "switch:2" << std::endl;
        break;
    default:
        std::cout << "switch:default" << std::endl;
        break;
    }
}

int main()
{
    threadTask5();

    int *main_arg = (int *)malloc(sizeof(int));
    if (main_arg) *main_arg = 41;

    if (pthread_create(&g_thread_lvl0, NULL, threadTask1, main_arg) != 0) {
        std::perror("pthread_create threadTask1 failed");
        if (main_arg) free(main_arg);
        return 1;
    }

    if (pthread_join(g_thread_lvl0, NULL) != 0) {
        std::perror("pthread_join lvl0 failed");
        return 1;
    }

    std::cout << "主线程完成" << std::endl;
    return 0;
}
