#include "time_stat.h"  // TA_INCLUDE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "include/task.h"

pthread_t thread, thread1, thread2, thread3;

void* threadtask3(void* arg) {
// TA_BEGIN: time_analysis.c:9 rad2deg
; /* TA_PAD */
uint64_t __ta_t0_threadtask3_rad2deg1_9_35 = now_ns();
    rad2deg(arg);
// TA_END: time_analysis.c:9 rad2deg
uint64_t __ta_t0_threadtask3_rad2deg1_9_35_dur = now_ns() - __ta_t0_threadtask3_rad2deg1_9_35;
time_account("threadtask3/rad2deg1", __ta_t0_threadtask3_rad2deg1_9_35_dur);
time_trace("threadtask3/rad2deg1", __ta_t0_threadtask3_rad2deg1_9_35, __ta_t0_threadtask3_rad2deg1_9_35_dur);
// TA_BEGIN: time_analysis.c:10 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask3_printf2_10_34 = now_ns();
    printf("task8结束\n");
// TA_END: time_analysis.c:10 printf
uint64_t __ta_t0_threadtask3_printf2_10_34_dur = now_ns() - __ta_t0_threadtask3_printf2_10_34;
time_account("threadtask3/printf2", __ta_t0_threadtask3_printf2_10_34_dur);
time_trace("threadtask3/printf2", __ta_t0_threadtask3_printf2_10_34, __ta_t0_threadtask3_printf2_10_34_dur);
    return NULL;
}
void* threadtask4(void* arg) {
// TA_BEGIN: time_analysis.c:14 prime
; /* TA_PAD */
uint64_t __ta_t0_threadtask4_prime1_14_33 = now_ns();
    prime(arg);
// TA_END: time_analysis.c:14 prime
uint64_t __ta_t0_threadtask4_prime1_14_33_dur = now_ns() - __ta_t0_threadtask4_prime1_14_33;
time_account("threadtask4/prime1", __ta_t0_threadtask4_prime1_14_33_dur);
time_trace("threadtask4/prime1", __ta_t0_threadtask4_prime1_14_33, __ta_t0_threadtask4_prime1_14_33_dur);
// TA_BEGIN: time_analysis.c:15 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask4_printf2_15_32 = now_ns();
    printf("task9结束\n");
// TA_END: time_analysis.c:15 printf
uint64_t __ta_t0_threadtask4_printf2_15_32_dur = now_ns() - __ta_t0_threadtask4_printf2_15_32;
time_account("threadtask4/printf2", __ta_t0_threadtask4_printf2_15_32_dur);
time_trace("threadtask4/printf2", __ta_t0_threadtask4_printf2_15_32, __ta_t0_threadtask4_printf2_15_32_dur);
    return NULL;
}
void* threadtask2(void* arg) {
// TA_BEGIN: time_analysis.c:19 malloc
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_malloc1_19_31 = now_ns();
    int* task_arg1 = malloc(sizeof(int));
// TA_END: time_analysis.c:19 malloc
uint64_t __ta_t0_threadtask2_malloc1_19_31_dur = now_ns() - __ta_t0_threadtask2_malloc1_19_31;
time_account("threadtask2/malloc1", __ta_t0_threadtask2_malloc1_19_31_dur);
time_trace("threadtask2/malloc1", __ta_t0_threadtask2_malloc1_19_31, __ta_t0_threadtask2_malloc1_19_31_dur);
// TA_BEGIN: time_analysis.c:20 malloc
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_malloc2_20_30 = now_ns();
    int* task_arg2 = malloc(sizeof(int));
// TA_END: time_analysis.c:20 malloc
uint64_t __ta_t0_threadtask2_malloc2_20_30_dur = now_ns() - __ta_t0_threadtask2_malloc2_20_30;
time_account("threadtask2/malloc2", __ta_t0_threadtask2_malloc2_20_30_dur);
time_trace("threadtask2/malloc2", __ta_t0_threadtask2_malloc2_20_30, __ta_t0_threadtask2_malloc2_20_30_dur);
    *task_arg1 = 43;
    *task_arg2 = 44;
// TA_BEGIN: time_analysis.c:23 minver
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_minver3_23_29 = now_ns();
    minver(arg);
// TA_END: time_analysis.c:23 minver
uint64_t __ta_t0_threadtask2_minver3_23_29_dur = now_ns() - __ta_t0_threadtask2_minver3_23_29;
time_account("threadtask2/minver3", __ta_t0_threadtask2_minver3_23_29_dur);
time_trace("threadtask2/minver3", __ta_t0_threadtask2_minver3_23_29, __ta_t0_threadtask2_minver3_23_29_dur);
// TA_BEGIN: time_analysis.c:24 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_printf4_24_28 = now_ns();
    printf("task5结束\n");
// TA_END: time_analysis.c:24 printf
uint64_t __ta_t0_threadtask2_printf4_24_28_dur = now_ns() - __ta_t0_threadtask2_printf4_24_28;
time_account("threadtask2/printf4", __ta_t0_threadtask2_printf4_24_28_dur);
time_trace("threadtask2/printf4", __ta_t0_threadtask2_printf4_24_28, __ta_t0_threadtask2_printf4_24_28_dur);
// TA_BEGIN: time_analysis.c:25 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_pthread_create5_25_27 = now_ns();
    pthread_create(&thread2, NULL, threadtask3, task_arg1); 
// TA_END: time_analysis.c:25 pthread_create
uint64_t __ta_t0_threadtask2_pthread_create5_25_27_dur = now_ns() - __ta_t0_threadtask2_pthread_create5_25_27;
time_account("threadtask2/pthread_create5", __ta_t0_threadtask2_pthread_create5_25_27_dur);
time_trace("threadtask2/pthread_create5", __ta_t0_threadtask2_pthread_create5_25_27, __ta_t0_threadtask2_pthread_create5_25_27_dur);
// TA_BEGIN: time_analysis.c:26 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_pthread_create6_26_26 = now_ns();
    pthread_create(&thread3, NULL, threadtask4, task_arg2);
// TA_END: time_analysis.c:26 pthread_create
uint64_t __ta_t0_threadtask2_pthread_create6_26_26_dur = now_ns() - __ta_t0_threadtask2_pthread_create6_26_26;
time_account("threadtask2/pthread_create6", __ta_t0_threadtask2_pthread_create6_26_26_dur);
time_trace("threadtask2/pthread_create6", __ta_t0_threadtask2_pthread_create6_26_26, __ta_t0_threadtask2_pthread_create6_26_26_dur);
// TA_BEGIN: time_analysis.c:27 ndes
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_ndes7_27_25 = now_ns();
    ndes(arg);
// TA_END: time_analysis.c:27 ndes
uint64_t __ta_t0_threadtask2_ndes7_27_25_dur = now_ns() - __ta_t0_threadtask2_ndes7_27_25;
time_account("threadtask2/ndes7", __ta_t0_threadtask2_ndes7_27_25_dur);
time_trace("threadtask2/ndes7", __ta_t0_threadtask2_ndes7_27_25, __ta_t0_threadtask2_ndes7_27_25_dur);
// TA_BEGIN: time_analysis.c:28 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_printf8_28_24 = now_ns();
    printf("task6结束\n");
// TA_END: time_analysis.c:28 printf
uint64_t __ta_t0_threadtask2_printf8_28_24_dur = now_ns() - __ta_t0_threadtask2_printf8_28_24;
time_account("threadtask2/printf8", __ta_t0_threadtask2_printf8_28_24_dur);
time_trace("threadtask2/printf8", __ta_t0_threadtask2_printf8_28_24, __ta_t0_threadtask2_printf8_28_24_dur);
// TA_BEGIN: time_analysis.c:29 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_pthread_join9_29_23 = now_ns();
    pthread_join(thread2, NULL);
// TA_END: time_analysis.c:29 pthread_join
uint64_t __ta_t0_threadtask2_pthread_join9_29_23_dur = now_ns() - __ta_t0_threadtask2_pthread_join9_29_23;
time_account("threadtask2/pthread_join9", __ta_t0_threadtask2_pthread_join9_29_23_dur);
time_trace("threadtask2/pthread_join9", __ta_t0_threadtask2_pthread_join9_29_23, __ta_t0_threadtask2_pthread_join9_29_23_dur);
// TA_BEGIN: time_analysis.c:30 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_pthread_join10_30_22 = now_ns();
    pthread_join(thread3, NULL);
// TA_END: time_analysis.c:30 pthread_join
uint64_t __ta_t0_threadtask2_pthread_join10_30_22_dur = now_ns() - __ta_t0_threadtask2_pthread_join10_30_22;
time_account("threadtask2/pthread_join10", __ta_t0_threadtask2_pthread_join10_30_22_dur);
time_trace("threadtask2/pthread_join10", __ta_t0_threadtask2_pthread_join10_30_22, __ta_t0_threadtask2_pthread_join10_30_22_dur);
// TA_BEGIN: time_analysis.c:31 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_free11_31_21 = now_ns();
    free(task_arg1); // 释放动态分配的内存
// TA_END: time_analysis.c:31 free
uint64_t __ta_t0_threadtask2_free11_31_21_dur = now_ns() - __ta_t0_threadtask2_free11_31_21;
time_account("threadtask2/free11", __ta_t0_threadtask2_free11_31_21_dur);
time_trace("threadtask2/free11", __ta_t0_threadtask2_free11_31_21, __ta_t0_threadtask2_free11_31_21_dur);
// TA_BEGIN: time_analysis.c:32 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_free12_32_20 = now_ns();
    free(task_arg2); // 释放动态分配的内存
// TA_END: time_analysis.c:32 free
uint64_t __ta_t0_threadtask2_free12_32_20_dur = now_ns() - __ta_t0_threadtask2_free12_32_20;
time_account("threadtask2/free12", __ta_t0_threadtask2_free12_32_20_dur);
time_trace("threadtask2/free12", __ta_t0_threadtask2_free12_32_20, __ta_t0_threadtask2_free12_32_20_dur);
// TA_BEGIN: time_analysis.c:33 ludcmp
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_ludcmp13_33_19 = now_ns();
    ludcmp(arg);
// TA_END: time_analysis.c:33 ludcmp
uint64_t __ta_t0_threadtask2_ludcmp13_33_19_dur = now_ns() - __ta_t0_threadtask2_ludcmp13_33_19;
time_account("threadtask2/ludcmp13", __ta_t0_threadtask2_ludcmp13_33_19_dur);
time_trace("threadtask2/ludcmp13", __ta_t0_threadtask2_ludcmp13_33_19, __ta_t0_threadtask2_ludcmp13_33_19_dur);
// TA_BEGIN: time_analysis.c:34 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_printf14_34_18 = now_ns();
    printf("task7结束\n");
// TA_END: time_analysis.c:34 printf
uint64_t __ta_t0_threadtask2_printf14_34_18_dur = now_ns() - __ta_t0_threadtask2_printf14_34_18;
time_account("threadtask2/printf14", __ta_t0_threadtask2_printf14_34_18_dur);
time_trace("threadtask2/printf14", __ta_t0_threadtask2_printf14_34_18, __ta_t0_threadtask2_printf14_34_18_dur);

    return NULL;
}
void* threadtask1(void* arg) {
// TA_BEGIN: time_analysis.c:39 malloc
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_malloc1_39_17 = now_ns();
    int* task_arg1 = malloc(sizeof(int));
// TA_END: time_analysis.c:39 malloc
uint64_t __ta_t0_threadtask1_malloc1_39_17_dur = now_ns() - __ta_t0_threadtask1_malloc1_39_17;
time_account("threadtask1/malloc1", __ta_t0_threadtask1_malloc1_39_17_dur);
time_trace("threadtask1/malloc1", __ta_t0_threadtask1_malloc1_39_17, __ta_t0_threadtask1_malloc1_39_17_dur);
    *task_arg1 = 42;
// TA_BEGIN: time_analysis.c:41 Deg2rad
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_Deg2rad2_41_16 = now_ns();
    Deg2rad(arg);
// TA_END: time_analysis.c:41 Deg2rad
uint64_t __ta_t0_threadtask1_Deg2rad2_41_16_dur = now_ns() - __ta_t0_threadtask1_Deg2rad2_41_16;
time_account("threadtask1/Deg2rad2", __ta_t0_threadtask1_Deg2rad2_41_16_dur);
time_trace("threadtask1/Deg2rad2", __ta_t0_threadtask1_Deg2rad2_41_16, __ta_t0_threadtask1_Deg2rad2_41_16_dur);
// TA_BEGIN: time_analysis.c:42 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf3_42_15 = now_ns();
    printf("task1结束\n");
// TA_END: time_analysis.c:42 printf
uint64_t __ta_t0_threadtask1_printf3_42_15_dur = now_ns() - __ta_t0_threadtask1_printf3_42_15;
time_account("threadtask1/printf3", __ta_t0_threadtask1_printf3_42_15_dur);
time_trace("threadtask1/printf3", __ta_t0_threadtask1_printf3_42_15, __ta_t0_threadtask1_printf3_42_15_dur);
// TA_BEGIN: time_analysis.c:43 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_pthread_create4_43_14 = now_ns();
    pthread_create(&thread1, NULL, threadtask2, task_arg1);
// TA_END: time_analysis.c:43 pthread_create
uint64_t __ta_t0_threadtask1_pthread_create4_43_14_dur = now_ns() - __ta_t0_threadtask1_pthread_create4_43_14;
time_account("threadtask1/pthread_create4", __ta_t0_threadtask1_pthread_create4_43_14_dur);
time_trace("threadtask1/pthread_create4", __ta_t0_threadtask1_pthread_create4_43_14, __ta_t0_threadtask1_pthread_create4_43_14_dur);
// TA_BEGIN: time_analysis.c:44 cover
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_cover5_44_13 = now_ns();
    cover(arg);
// TA_END: time_analysis.c:44 cover
uint64_t __ta_t0_threadtask1_cover5_44_13_dur = now_ns() - __ta_t0_threadtask1_cover5_44_13;
time_account("threadtask1/cover5", __ta_t0_threadtask1_cover5_44_13_dur);
time_trace("threadtask1/cover5", __ta_t0_threadtask1_cover5_44_13, __ta_t0_threadtask1_cover5_44_13_dur);
// TA_BEGIN: time_analysis.c:45 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf6_45_12 = now_ns();
    printf("task2结束\n");
// TA_END: time_analysis.c:45 printf
uint64_t __ta_t0_threadtask1_printf6_45_12_dur = now_ns() - __ta_t0_threadtask1_printf6_45_12;
time_account("threadtask1/printf6", __ta_t0_threadtask1_printf6_45_12_dur);
time_trace("threadtask1/printf6", __ta_t0_threadtask1_printf6_45_12, __ta_t0_threadtask1_printf6_45_12_dur);
// TA_BEGIN: time_analysis.c:46 duff
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_duff7_46_11 = now_ns();
    duff(arg);
// TA_END: time_analysis.c:46 duff
uint64_t __ta_t0_threadtask1_duff7_46_11_dur = now_ns() - __ta_t0_threadtask1_duff7_46_11;
time_account("threadtask1/duff7", __ta_t0_threadtask1_duff7_46_11_dur);
time_trace("threadtask1/duff7", __ta_t0_threadtask1_duff7_46_11, __ta_t0_threadtask1_duff7_46_11_dur);
// TA_BEGIN: time_analysis.c:47 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf8_47_10 = now_ns();
    printf("task3结束\n");
// TA_END: time_analysis.c:47 printf
uint64_t __ta_t0_threadtask1_printf8_47_10_dur = now_ns() - __ta_t0_threadtask1_printf8_47_10;
time_account("threadtask1/printf8", __ta_t0_threadtask1_printf8_47_10_dur);
time_trace("threadtask1/printf8", __ta_t0_threadtask1_printf8_47_10, __ta_t0_threadtask1_printf8_47_10_dur);
// TA_BEGIN: time_analysis.c:48 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_pthread_join9_48_9 = now_ns();
    pthread_join(thread1, NULL);
// TA_END: time_analysis.c:48 pthread_join
uint64_t __ta_t0_threadtask1_pthread_join9_48_9_dur = now_ns() - __ta_t0_threadtask1_pthread_join9_48_9;
time_account("threadtask1/pthread_join9", __ta_t0_threadtask1_pthread_join9_48_9_dur);
time_trace("threadtask1/pthread_join9", __ta_t0_threadtask1_pthread_join9_48_9, __ta_t0_threadtask1_pthread_join9_48_9_dur);
// TA_BEGIN: time_analysis.c:49 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_free10_49_8 = now_ns();
    free(task_arg1); // 释放动态分配的内存
// TA_END: time_analysis.c:49 free
uint64_t __ta_t0_threadtask1_free10_49_8_dur = now_ns() - __ta_t0_threadtask1_free10_49_8;
time_account("threadtask1/free10", __ta_t0_threadtask1_free10_49_8_dur);
time_trace("threadtask1/free10", __ta_t0_threadtask1_free10_49_8, __ta_t0_threadtask1_free10_49_8_dur);
// TA_BEGIN: time_analysis.c:50 insertsort
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_insertsort11_50_7 = now_ns();
    insertsort(arg);
// TA_END: time_analysis.c:50 insertsort
uint64_t __ta_t0_threadtask1_insertsort11_50_7_dur = now_ns() - __ta_t0_threadtask1_insertsort11_50_7;
time_account("threadtask1/insertsort11", __ta_t0_threadtask1_insertsort11_50_7_dur);
time_trace("threadtask1/insertsort11", __ta_t0_threadtask1_insertsort11_50_7, __ta_t0_threadtask1_insertsort11_50_7_dur);
// TA_BEGIN: time_analysis.c:51 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf12_51_6 = now_ns();
    printf("task4结束\n");
// TA_END: time_analysis.c:51 printf
uint64_t __ta_t0_threadtask1_printf12_51_6_dur = now_ns() - __ta_t0_threadtask1_printf12_51_6;
time_account("threadtask1/printf12", __ta_t0_threadtask1_printf12_51_6_dur);
time_trace("threadtask1/printf12", __ta_t0_threadtask1_printf12_51_6, __ta_t0_threadtask1_printf12_51_6_dur);
    return NULL;
}


int main() {
// TA_BEGIN: time_analysis.c:57 malloc
; /* TA_PAD */
uint64_t __ta_t0_main_malloc1_57_5 = now_ns();
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
// TA_END: time_analysis.c:57 malloc
uint64_t __ta_t0_main_malloc1_57_5_dur = now_ns() - __ta_t0_main_malloc1_57_5;
time_account("main/malloc1", __ta_t0_main_malloc1_57_5_dur);
time_trace("main/malloc1", __ta_t0_main_malloc1_57_5, __ta_t0_main_malloc1_57_5_dur);
    *task_arg = 41; // 设置任务参数
    // 创建线程并绑定任务函数
// TA_BEGIN: time_analysis.c:60 pthread_create
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_create2_60_4 = now_ns();
    pthread_create(&thread, NULL, threadtask1, task_arg);
// TA_END: time_analysis.c:60 pthread_create
uint64_t __ta_t0_main_pthread_create2_60_4_dur = now_ns() - __ta_t0_main_pthread_create2_60_4;
time_account("main/pthread_create2", __ta_t0_main_pthread_create2_60_4_dur);
time_trace("main/pthread_create2", __ta_t0_main_pthread_create2_60_4, __ta_t0_main_pthread_create2_60_4_dur);
// TA_BEGIN: time_analysis.c:61 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_main_pthread_join3_61_3 = now_ns();
    pthread_join(thread, NULL);
// TA_END: time_analysis.c:61 pthread_join
uint64_t __ta_t0_main_pthread_join3_61_3_dur = now_ns() - __ta_t0_main_pthread_join3_61_3;
time_account("main/pthread_join3", __ta_t0_main_pthread_join3_61_3_dur);
time_trace("main/pthread_join3", __ta_t0_main_pthread_join3_61_3, __ta_t0_main_pthread_join3_61_3_dur);
// TA_BEGIN: time_analysis.c:62 free
; /* TA_PAD */
uint64_t __ta_t0_main_free4_62_2 = now_ns();
    free(task_arg); // 释放动态分配的内存
// TA_END: time_analysis.c:62 free
uint64_t __ta_t0_main_free4_62_2_dur = now_ns() - __ta_t0_main_free4_62_2;
time_account("main/free4", __ta_t0_main_free4_62_2_dur);
time_trace("main/free4", __ta_t0_main_free4_62_2, __ta_t0_main_free4_62_2_dur);
// TA_BEGIN: time_analysis.c:63 printf
; /* TA_PAD */
uint64_t __ta_t0_main_printf5_63_1 = now_ns();
    printf("主线程已完成\n");
// TA_END: time_analysis.c:63 printf
uint64_t __ta_t0_main_printf5_63_1_dur = now_ns() - __ta_t0_main_printf5_63_1;
time_account("main/printf5", __ta_t0_main_printf5_63_1_dur);
time_trace("main/printf5", __ta_t0_main_printf5_63_1, __ta_t0_main_printf5_63_1_dur);
    return 0;
}
