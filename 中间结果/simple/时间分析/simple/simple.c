#include "time_stat.h"  // TA_INCLUDE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
pthread_t thread;
void* threadtask1(void* arg) {
// TA_BEGIN: simple.c:6 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf1_6_6 = now_ns();
    printf("task1结束\n");
// TA_END: simple.c:6 printf
time_account("threadtask1/printf1", now_ns() - __ta_t0_threadtask1_printf1_6_6);
    return NULL;
}
int main() {
// TA_BEGIN: simple.c:10 malloc
; /* TA_PAD */
uint64_t __ta_t0_main_malloc1_10_5 = now_ns();
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
// TA_END: simple.c:10 malloc
time_account("main/malloc1", now_ns() - __ta_t0_main_malloc1_10_5);
    *task_arg = 41; // 设置任务参数
    // 创建线程并绑定任务函数
// TA_BEGIN: simple.c:13 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create2_13_4 = now_ns();
    pthread_create(&thread, NULL, threadtask1, task_arg);
// TA_END: simple.c:13 pthread_create
time_account("main/pthread_create2", now_ns() - __ta_t0_main_pthread_create2_13_4);
// TA_BEGIN: simple.c:14 printf
; /* TA_PAD */
uint64_t __ta_t0_main_printf3_14_3 = now_ns();
    printf("主线程继续执行其他任务...\n");
// TA_END: simple.c:14 printf
time_account("main/printf3", now_ns() - __ta_t0_main_printf3_14_3);
// TA_BEGIN: simple.c:15 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join4_15_2 = now_ns();
    pthread_join(thread, NULL); 
// TA_END: simple.c:15 pthread_join
time_account("main/pthread_join4", now_ns() - __ta_t0_main_pthread_join4_15_2);
// TA_BEGIN: simple.c:16 free
; /* TA_PAD */
uint64_t __ta_t0_main_free5_16_1 = now_ns();
    free(task_arg); // 释放动态分配的内存
// TA_END: simple.c:16 free
time_account("main/free5", now_ns() - __ta_t0_main_free5_16_1);
    return 0;
}