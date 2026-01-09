#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "include/task.h"

pthread_t thread, thread1, thread2, thread3;

void* threadtask3(void* arg) {
    rad2deg(arg);
    printf("task8结束\n");
    return NULL;
}
void* threadtask4(void* arg) {
    prime(arg);
    printf("task9结束\n");
    return NULL;
}
void* threadtask2(void* arg) {
    int* task_arg1 = malloc(sizeof(int));
    int* task_arg2 = malloc(sizeof(int));
    *task_arg1 = 43;
    *task_arg2 = 44;
    minver(arg);
    printf("task5结束\n");
    pthread_create(&thread2, NULL, threadtask3, task_arg1); 
    pthread_create(&thread3, NULL, threadtask4, task_arg2);
    ndes(arg);
    printf("task6结束\n");
    pthread_join(thread2, NULL);
    pthread_join(thread3, NULL);
    free(task_arg1); // 释放动态分配的内存
    free(task_arg2); // 释放动态分配的内存
    ludcmp(arg);
    printf("task7结束\n");

    return NULL;
}
void* threadtask1(void* arg) {
    int* task_arg1 = malloc(sizeof(int));
    *task_arg1 = 42;
    Deg2rad(arg);
    printf("task1结束\n");
    pthread_create(&thread1, NULL, threadtask2, task_arg1);
    cover(arg);
    printf("task2结束\n");
    duff(arg);
    printf("task3结束\n");
    pthread_join(thread1, NULL);
    free(task_arg1); // 释放动态分配的内存
    insertsort(arg);
    printf("task4结束\n");
    return NULL;
}


int main() {
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
    *task_arg = 41; // 设置任务参数
    // 创建线程并绑定任务函数
    pthread_create(&thread, NULL, threadtask1, task_arg);
    pthread_join(thread, NULL);
    free(task_arg); // 释放动态分配的内存
    printf("主线程已完成\n");
    return 0;
}
