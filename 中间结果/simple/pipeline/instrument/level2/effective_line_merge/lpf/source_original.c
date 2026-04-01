#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
pthread_t thread;
void* threadtask1(void* arg) {
    printf("task1结束\n");
    return NULL;
}
int main() {
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
    *task_arg = 41; // 设置任务参数
    // 创建线程并绑定任务函数
    pthread_create(&thread, NULL, threadtask1, task_arg);
    printf("主线程继续执行其他任务...\n");
    pthread_join(thread, NULL); 
    free(task_arg); // 释放动态分配的内存
    return 0;
}