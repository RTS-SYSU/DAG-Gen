#include "segtrace.h"
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
pthread_t thread;
void* threadtask1(void* arg) {
SEG_BEGIN("SEG:threadtask1#001@6-6");
    printf("task1结束\n");
SEG_END("SEG:threadtask1#001@6-6");
    return NULL;
}
int main() {
SEG_BEGIN("SEG:main#001@10-13");
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
    *task_arg = 41; // 设置任务参数
    // 创建线程并绑定任务函数
    pthread_create(&thread, NULL, threadtask1, task_arg);
SEG_END("SEG:main#001@10-13");
SEG_BEGIN("SEG:main#002@14-14");
    printf("主线程继续执行其他任务...\n");
SEG_END("SEG:main#002@14-14");
SEG_BEGIN("SEG:main#003@15-16");
    pthread_join(thread, NULL); 
    free(task_arg); // 释放动态分配的内存
SEG_END("SEG:main#003@15-16");
    return 0;
}