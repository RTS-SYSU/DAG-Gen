#include "prio_runtime.h"
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
pthread_t thread;
void* threadtask1(void* arg) {
    l1_set_thread_prio_fifo(96);
    printf("task1结束\n");
    return NULL;
}
int main() {
    l1_set_thread_prio_fifo(98);
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
    *task_arg = 41; // 设置任务参数
    // 创建线程并绑定任务函数
    pthread_create(&thread, NULL, threadtask1, task_arg);
    l1_set_thread_prio_fifo(97);
    printf("主线程继续执行其他任务...\n");
    l1_set_thread_prio_fifo(99);
    pthread_join(thread, NULL); 
    free(task_arg); // 释放动态分配的内存
    return 0;
}