#include "time_stat.h"  // TA_INCLUDE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "include/task.h"

pthread_t thread, thread1, thread2, thread3;
// 任务函数
void* task(void* arg) {
    int* num = (int*)arg;
// TA_BEGIN: main.c:10 printf
do {
uint64_t __ta_t0_main_c_10_25 = now_ns();
    printf("线程正在处理任务, 参数值为: %d\n", *num);
// TA_END: main.c:10 printf
time_account("printf@main.c:10", now_ns() - __ta_t0_main_c_10_25);
} while (0);
    int i = 0;
    while (i < 100000) {
        i++;
    }
    return NULL;
}
void* threadtask3(void* arg) {
    rad2deg(arg);
// TA_BEGIN: main.c:19 printf
do {
uint64_t __ta_t0_main_c_19_24 = now_ns();
    printf("task8结束\n");
// TA_END: main.c:19 printf
time_account("printf@main.c:19", now_ns() - __ta_t0_main_c_19_24);
} while (0);
    return NULL;
}
void* threadtask4(void* arg) {
    prime(arg);
// TA_BEGIN: main.c:24 printf
do {
uint64_t __ta_t0_main_c_24_23 = now_ns();
    printf("task9结束\n");
// TA_END: main.c:24 printf
time_account("printf@main.c:24", now_ns() - __ta_t0_main_c_24_23);
} while (0);
    return NULL;
}
void* threadtask2(void* arg) {
    int* task_arg1 = malloc(sizeof(int));
    int* task_arg2 = malloc(sizeof(int));
    *task_arg1 = 43;
    *task_arg2 = 44;

// TA_BEGIN: main.c:33 minver
do {
uint64_t __ta_t0_main_c_33_22 = now_ns();
    minver(arg);
// TA_END: main.c:33 minver
time_account("minver@main.c:33", now_ns() - __ta_t0_main_c_33_22);
} while (0);
    printf("task5结束\n");

    if (pthread_create(&thread2, NULL, threadtask3, task_arg1) != 0) {
// TA_BEGIN: main.c:37 fprintf
do {
uint64_t __ta_t0_main_c_37_21 = now_ns();
        fprintf(stderr, "线程创建失败\n");
// TA_END: main.c:37 fprintf
time_account("fprintf@main.c:37", now_ns() - __ta_t0_main_c_37_21);
} while (0);
        free(task_arg1); // 如果线程创建失败，释放内存
        return NULL;
    }
    
    if (pthread_create(&thread3, NULL, threadtask4, task_arg2) != 0) {
        fprintf(stderr, "线程创建失败\n");
// TA_BEGIN: main.c:44 free
do {
uint64_t __ta_t0_main_c_44_20 = now_ns();
        free(task_arg1); // 如果线程创建失败，释放内存
// TA_END: main.c:44 free
time_account("free@main.c:44", now_ns() - __ta_t0_main_c_44_20);
} while (0);
        return NULL;
    }
    ndes(arg);
// TA_BEGIN: main.c:48 printf
do {
uint64_t __ta_t0_main_c_48_19 = now_ns();
    printf("task6结束\n");
// TA_END: main.c:48 printf
time_account("printf@main.c:48", now_ns() - __ta_t0_main_c_48_19);
} while (0);
    pthread_join(thread2, NULL);
    pthread_join(thread3, NULL);
// TA_BEGIN: main.c:51 free
do {
uint64_t __ta_t0_main_c_51_18 = now_ns();
    free(task_arg1); // 释放动态分配的内存
// TA_END: main.c:51 free
time_account("free@main.c:51", now_ns() - __ta_t0_main_c_51_18);
} while (0);
    free(task_arg2); // 释放动态分配的内存
    ludcmp(arg);
// TA_BEGIN: main.c:54 printf
do {
uint64_t __ta_t0_main_c_54_17 = now_ns();
    printf("task7结束\n");
// TA_END: main.c:54 printf
time_account("printf@main.c:54", now_ns() - __ta_t0_main_c_54_17);
} while (0);

    return NULL;
}
void* threadtask1(void* arg) {
    int* task_arg1 = malloc(sizeof(int));
    if (task_arg1 == NULL) {
// TA_BEGIN: main.c:61 fprintf
do {
uint64_t __ta_t0_main_c_61_16 = now_ns();
        fprintf(stderr, "内存分配失败\n");
// TA_END: main.c:61 fprintf
time_account("fprintf@main.c:61", now_ns() - __ta_t0_main_c_61_16);
} while (0);
        return NULL;
    }
    *task_arg1 = 42;

// TA_BEGIN: main.c:66 Deg2rad
do {
uint64_t __ta_t0_main_c_66_15 = now_ns();
    Deg2rad(arg);
// TA_END: main.c:66 Deg2rad
time_account("Deg2rad@main.c:66", now_ns() - __ta_t0_main_c_66_15);
} while (0);
    printf("task1结束\n");

    if (pthread_create(&thread1, NULL,threadtask2, task_arg1) != 0) {
        fprintf(stderr, "线程创建失败\n");
// TA_BEGIN: main.c:71 free
do {
uint64_t __ta_t0_main_c_71_14 = now_ns();
        free(task_arg1); // 如果线程创建失败，释放内存
// TA_END: main.c:71 free
time_account("free@main.c:71", now_ns() - __ta_t0_main_c_71_14);
} while (0);
        return NULL;
    }

    cover(arg);
// TA_BEGIN: main.c:76 printf
do {
uint64_t __ta_t0_main_c_76_13 = now_ns();
    printf("task2结束\n");
// TA_END: main.c:76 printf
time_account("printf@main.c:76", now_ns() - __ta_t0_main_c_76_13);
} while (0);
    duff(arg);
    printf("task3结束\n");
// TA_BEGIN: main.c:79 pthread_join
do {
uint64_t __ta_t0_main_c_79_12 = now_ns();
    pthread_join(thread1, NULL);
// TA_END: main.c:79 pthread_join
time_account("pthread_join@main.c:79", now_ns() - __ta_t0_main_c_79_12);
} while (0);
    free(task_arg1); // 释放动态分配的内存    
    insertsort(arg);
// TA_BEGIN: main.c:82 printf
do {
uint64_t __ta_t0_main_c_82_11 = now_ns();
    printf("task4结束\n");
// TA_END: main.c:82 printf
time_account("printf@main.c:82", now_ns() - __ta_t0_main_c_82_11);
} while (0);
    return NULL;
}
void threadtask5()
{
    int i = 0;
    while (i < 3)
    {
// TA_BEGIN: main.c:90 printf
do {
uint64_t __ta_t0_main_c_90_10 = now_ns();
        printf("while循环测试\n");
// TA_END: main.c:90 printf
time_account("printf@main.c:90", now_ns() - __ta_t0_main_c_90_10);
} while (0);
        i++;
    }
    do
    {
// TA_BEGIN: main.c:95 printf
do {
uint64_t __ta_t0_main_c_95_9 = now_ns();
        printf("do-while循环测试\n");
// TA_END: main.c:95 printf
time_account("printf@main.c:95", now_ns() - __ta_t0_main_c_95_9);
} while (0);
        i--;
    } while (i == 0);
    for (int i = 0; i < 5; i++)
    {
// TA_BEGIN: main.c:100 printf
do {
uint64_t __ta_t0_main_c_100_8 = now_ns();
        printf("for循环测试\n");
// TA_END: main.c:100 printf
time_account("printf@main.c:100", now_ns() - __ta_t0_main_c_100_8);
} while (0);
    }
    int j = 2;
    switch (j)
    {
    case 1:
// TA_BEGIN: main.c:106 printf
do {
uint64_t __ta_t0_main_c_106_7 = now_ns();
        printf("switch:1测试\n");
// TA_END: main.c:106 printf
time_account("printf@main.c:106", now_ns() - __ta_t0_main_c_106_7);
} while (0);
        break;
    case 2:
// TA_BEGIN: main.c:109 printf
do {
uint64_t __ta_t0_main_c_109_6 = now_ns();
        printf("switch:2测试\n");
// TA_END: main.c:109 printf
time_account("printf@main.c:109", now_ns() - __ta_t0_main_c_109_6);
} while (0);
        break;
    default:
// TA_BEGIN: main.c:112 printf
do {
uint64_t __ta_t0_main_c_112_5 = now_ns();
        printf("hello\n");
// TA_END: main.c:112 printf
time_account("printf@main.c:112", now_ns() - __ta_t0_main_c_112_5);
} while (0);
        break;
    }
}

int main() {
// TA_BEGIN: main.c:118 threadtask
do {
uint64_t __ta_t0_main_c_118_4 = now_ns();
    threadtask5();
// TA_END: main.c:118 threadtask
time_account("threadtask@main.c:118", now_ns() - __ta_t0_main_c_118_4);
} while (0);
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
    if (task_arg == NULL) {
        fprintf(stderr, "内存分配失败\n");
        return 1;
    }
    *task_arg = 41; // 设置任务参数

    // 创建线程并绑定任务函数
    if (pthread_create(&thread, NULL, threadtask1, task_arg) != 0) {
        fprintf(stderr, "线程创建失败\n");
// TA_BEGIN: main.c:129 free
do {
uint64_t __ta_t0_main_c_129_3 = now_ns();
        free(task_arg); // 如果线程创建失败，释放内存
// TA_END: main.c:129 free
time_account("free@main.c:129", now_ns() - __ta_t0_main_c_129_3);
} while (0);
        return 1;
    }

    if (pthread_join(thread, NULL) != 0) {
        fprintf(stderr, "等待线程完成失败\n");
// TA_BEGIN: main.c:135 free
do {
uint64_t __ta_t0_main_c_135_2 = now_ns();
        free(task_arg); // 确保释放内存
// TA_END: main.c:135 free
time_account("free@main.c:135", now_ns() - __ta_t0_main_c_135_2);
} while (0);
        return 1;
    }

    free(task_arg); // 释放动态分配的内存
// TA_BEGIN: main.c:140 printf
do {
uint64_t __ta_t0_main_c_140_1 = now_ns();
    printf("主线程已完成\n");
// TA_END: main.c:140 printf
time_account("printf@main.c:140", now_ns() - __ta_t0_main_c_140_1);
} while (0);
    return 0;
}