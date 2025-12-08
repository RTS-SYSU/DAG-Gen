#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "include/task.h"

pthread_t thread, thread1, thread2, thread3;
// 任务函数
void* task(void* arg) {
    int* num = (int*)arg;
    printf("线程正在处理任务, 参数值为: %d\n", *num);
    int i = 0;
    while (i < 100000) {
        i++;
    }
    return NULL;
}
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

    if (pthread_create(&thread2, NULL, threadtask3, task_arg1) != 0) {
        fprintf(stderr, "线程创建失败\n");
        free(task_arg1); // 如果线程创建失败，释放内存
        return NULL;
    }
    
    if (pthread_create(&thread3, NULL, threadtask4, task_arg2) != 0) {
        fprintf(stderr, "线程创建失败\n");
        free(task_arg1); // 如果线程创建失败，释放内存
        return NULL;
    }
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
    if (task_arg1 == NULL) {
        fprintf(stderr, "内存分配失败\n");
        return NULL;
    }
    *task_arg1 = 42;

    Deg2rad(arg);
    printf("task1结束\n");

    if (pthread_create(&thread1, NULL,threadtask2, task_arg1) != 0) {
        fprintf(stderr, "线程创建失败\n");
        free(task_arg1); // 如果线程创建失败，释放内存
        return NULL;
    }

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
void threadtask5()
{
    int i = 0;
    while (i < 3)
    {
        printf("while循环测试\n");
        i++;
    }
    do
    {
        printf("do-while循环测试\n");
        i--;
    } while (i == 0);
    for (int i = 0; i < 5; i++)
    {
        printf("for循环测试\n");
    }
    int j = 2;
    switch (j)
    {
    case 1:
        printf("switch:1测试\n");
        break;
    case 2:
        printf("switch:2测试\n");
        break;
    default:
        printf("hello\n");
        break;
    }
}

int main() {
    threadtask5();
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
    if (task_arg == NULL) {
        fprintf(stderr, "内存分配失败\n");
        return 1;
    }
    *task_arg = 41; // 设置任务参数

    // 创建线程并绑定任务函数
    if (pthread_create(&thread, NULL, threadtask1, task_arg) != 0) {
        fprintf(stderr, "线程创建失败\n");
        free(task_arg); // 如果线程创建失败，释放内存
        return 1;
    }

    if (pthread_join(thread, NULL) != 0) {
        fprintf(stderr, "等待线程完成失败\n");
        free(task_arg); // 确保释放内存
        return 1;
    }

    free(task_arg); // 释放动态分配的内存
    printf("主线程已完成\n");
    return 0;
}