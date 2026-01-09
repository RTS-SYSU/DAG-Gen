#include "time_stat.h"  // TA_INCLUDE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "include/task.h"

pthread_t thread, thread1, thread2, thread3;

void* threadtask3(void* arg) {
// TA_BEGIN: main1.c:9 rad2deg
; /* TA_PAD */
uint64_t __ta_t0_threadtask3_rad2deg1_9_53 = now_ns();
    rad2deg(arg);
// TA_END: main1.c:9 rad2deg
time_account("threadtask3/rad2deg1", now_ns() - __ta_t0_threadtask3_rad2deg1_9_53);
// TA_BEGIN: main1.c:10 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask3_printf2_10_52 = now_ns();
    printf("task8结束\n");
// TA_END: main1.c:10 printf
time_account("threadtask3/printf2", now_ns() - __ta_t0_threadtask3_printf2_10_52);
    return NULL;
}
void* threadtask4(void* arg) {
// TA_BEGIN: main1.c:14 prime
; /* TA_PAD */
uint64_t __ta_t0_threadtask4_prime1_14_51 = now_ns();
    prime(arg);
// TA_END: main1.c:14 prime
time_account("threadtask4/prime1", now_ns() - __ta_t0_threadtask4_prime1_14_51);
// TA_BEGIN: main1.c:15 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask4_printf2_15_50 = now_ns();
    printf("task9结束\n");
// TA_END: main1.c:15 printf
time_account("threadtask4/printf2", now_ns() - __ta_t0_threadtask4_printf2_15_50);
    return NULL;
}
void* threadtask2(void* arg) {
// TA_BEGIN: main1.c:19 malloc
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_malloc1_19_49 = now_ns();
    int* task_arg1 = malloc(sizeof(int));
// TA_END: main1.c:19 malloc
time_account("threadtask2/malloc1", now_ns() - __ta_t0_threadtask2_malloc1_19_49);
// TA_BEGIN: main1.c:20 malloc
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_malloc2_20_48 = now_ns();
    int* task_arg2 = malloc(sizeof(int));
// TA_END: main1.c:20 malloc
time_account("threadtask2/malloc2", now_ns() - __ta_t0_threadtask2_malloc2_20_48);
    *task_arg1 = 43;
    *task_arg2 = 44;

// TA_BEGIN: main1.c:24 minver
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_minver3_24_47 = now_ns();
    minver(arg);
// TA_END: main1.c:24 minver
time_account("threadtask2/minver3", now_ns() - __ta_t0_threadtask2_minver3_24_47);
// TA_BEGIN: main1.c:25 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_printf4_25_46 = now_ns();
    printf("task5结束\n");
// TA_END: main1.c:25 printf
time_account("threadtask2/printf4", now_ns() - __ta_t0_threadtask2_printf4_25_46);

    if ((__extension__({ uint64_t __ta_t0_threadtask2_pthread_create5_27_45 = now_ns(); __auto_type __ta_ret = pthread_create(&thread2, NULL, threadtask3, task_arg1); time_account("threadtask2/pthread_create5", now_ns() - __ta_t0_threadtask2_pthread_create5_27_45); __ta_ret; })) != 0) {
// TA_BEGIN: main1.c:28 fprintf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_if_fprintf6_28_44 = now_ns();
        fprintf(stderr, "线程创建失败\n");
// TA_END: main1.c:28 fprintf
time_account("threadtask2/if/fprintf6", now_ns() - __ta_t0_threadtask2_if_fprintf6_28_44);
// TA_BEGIN: main1.c:29 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_if_free7_29_43 = now_ns();
        free(task_arg1); // 如果线程创建失败，释放内存
// TA_END: main1.c:29 free
time_account("threadtask2/if/free7", now_ns() - __ta_t0_threadtask2_if_free7_29_43);
        return NULL;
    }
    
    if ((__extension__({ uint64_t __ta_t0_threadtask2_pthread_create8_33_42 = now_ns(); __auto_type __ta_ret = pthread_create(&thread3, NULL, threadtask4, task_arg2); time_account("threadtask2/pthread_create8", now_ns() - __ta_t0_threadtask2_pthread_create8_33_42); __ta_ret; })) != 0) {
// TA_BEGIN: main1.c:34 fprintf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_if_fprintf9_34_41 = now_ns();
        fprintf(stderr, "线程创建失败\n");
// TA_END: main1.c:34 fprintf
time_account("threadtask2/if/fprintf9", now_ns() - __ta_t0_threadtask2_if_fprintf9_34_41);
// TA_BEGIN: main1.c:35 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_if_free10_35_40 = now_ns();
        free(task_arg1); // 如果线程创建失败，释放内存
// TA_END: main1.c:35 free
time_account("threadtask2/if/free10", now_ns() - __ta_t0_threadtask2_if_free10_35_40);
        return NULL;
    }
// TA_BEGIN: main1.c:38 ndes
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_ndes11_38_39 = now_ns();
    ndes(arg);
// TA_END: main1.c:38 ndes
time_account("threadtask2/ndes11", now_ns() - __ta_t0_threadtask2_ndes11_38_39);
// TA_BEGIN: main1.c:39 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_printf12_39_38 = now_ns();
    printf("task6结束\n");
// TA_END: main1.c:39 printf
time_account("threadtask2/printf12", now_ns() - __ta_t0_threadtask2_printf12_39_38);
// TA_BEGIN: main1.c:40 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_pthread_join13_40_37 = now_ns();
    pthread_join(thread2, NULL);
// TA_END: main1.c:40 pthread_join
time_account("threadtask2/pthread_join13", now_ns() - __ta_t0_threadtask2_pthread_join13_40_37);
// TA_BEGIN: main1.c:41 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_pthread_join14_41_36 = now_ns();
    pthread_join(thread3, NULL);
// TA_END: main1.c:41 pthread_join
time_account("threadtask2/pthread_join14", now_ns() - __ta_t0_threadtask2_pthread_join14_41_36);
// TA_BEGIN: main1.c:42 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_free15_42_35 = now_ns();
    free(task_arg1); // 释放动态分配的内存
// TA_END: main1.c:42 free
time_account("threadtask2/free15", now_ns() - __ta_t0_threadtask2_free15_42_35);
// TA_BEGIN: main1.c:43 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_free16_43_34 = now_ns();
    free(task_arg2); // 释放动态分配的内存
// TA_END: main1.c:43 free
time_account("threadtask2/free16", now_ns() - __ta_t0_threadtask2_free16_43_34);
// TA_BEGIN: main1.c:44 ludcmp
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_ludcmp17_44_33 = now_ns();
    ludcmp(arg);
// TA_END: main1.c:44 ludcmp
time_account("threadtask2/ludcmp17", now_ns() - __ta_t0_threadtask2_ludcmp17_44_33);
// TA_BEGIN: main1.c:45 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_printf18_45_32 = now_ns();
    printf("task7结束\n");
// TA_END: main1.c:45 printf
time_account("threadtask2/printf18", now_ns() - __ta_t0_threadtask2_printf18_45_32);

    return NULL;
}
void* threadtask1(void* arg) {
// TA_BEGIN: main1.c:50 malloc
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_malloc1_50_31 = now_ns();
    int* task_arg1 = malloc(sizeof(int));
// TA_END: main1.c:50 malloc
time_account("threadtask1/malloc1", now_ns() - __ta_t0_threadtask1_malloc1_50_31);
    if (task_arg1 == NULL) {
// TA_BEGIN: main1.c:52 fprintf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_if_fprintf2_52_30 = now_ns();
        fprintf(stderr, "内存分配失败\n");
// TA_END: main1.c:52 fprintf
time_account("threadtask1/if/fprintf2", now_ns() - __ta_t0_threadtask1_if_fprintf2_52_30);
        return NULL;
    }
    *task_arg1 = 42;

// TA_BEGIN: main1.c:57 Deg2rad
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_Deg2rad3_57_29 = now_ns();
    Deg2rad(arg);
// TA_END: main1.c:57 Deg2rad
time_account("threadtask1/Deg2rad3", now_ns() - __ta_t0_threadtask1_Deg2rad3_57_29);
// TA_BEGIN: main1.c:58 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf4_58_28 = now_ns();
    printf("task1结束\n");
// TA_END: main1.c:58 printf
time_account("threadtask1/printf4", now_ns() - __ta_t0_threadtask1_printf4_58_28);

    if ((__extension__({ uint64_t __ta_t0_threadtask1_pthread_create5_60_27 = now_ns(); __auto_type __ta_ret = pthread_create(&thread1, NULL,threadtask2, task_arg1); time_account("threadtask1/pthread_create5", now_ns() - __ta_t0_threadtask1_pthread_create5_60_27); __ta_ret; })) != 0) {
// TA_BEGIN: main1.c:61 fprintf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_if_fprintf6_61_26 = now_ns();
        fprintf(stderr, "线程创建失败\n");
// TA_END: main1.c:61 fprintf
time_account("threadtask1/if/fprintf6", now_ns() - __ta_t0_threadtask1_if_fprintf6_61_26);
// TA_BEGIN: main1.c:62 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_if_free7_62_25 = now_ns();
        free(task_arg1); // 如果线程创建失败，释放内存
// TA_END: main1.c:62 free
time_account("threadtask1/if/free7", now_ns() - __ta_t0_threadtask1_if_free7_62_25);
        return NULL;
    }

// TA_BEGIN: main1.c:66 cover
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_cover8_66_24 = now_ns();
    cover(arg);
// TA_END: main1.c:66 cover
time_account("threadtask1/cover8", now_ns() - __ta_t0_threadtask1_cover8_66_24);
// TA_BEGIN: main1.c:67 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf9_67_23 = now_ns();
    printf("task2结束\n");
// TA_END: main1.c:67 printf
time_account("threadtask1/printf9", now_ns() - __ta_t0_threadtask1_printf9_67_23);
// TA_BEGIN: main1.c:68 duff
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_duff10_68_22 = now_ns();
    duff(arg);
// TA_END: main1.c:68 duff
time_account("threadtask1/duff10", now_ns() - __ta_t0_threadtask1_duff10_68_22);
// TA_BEGIN: main1.c:69 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf11_69_21 = now_ns();
    printf("task3结束\n");
// TA_END: main1.c:69 printf
time_account("threadtask1/printf11", now_ns() - __ta_t0_threadtask1_printf11_69_21);
// TA_BEGIN: main1.c:70 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_pthread_join12_70_20 = now_ns();
    pthread_join(thread1, NULL);
// TA_END: main1.c:70 pthread_join
time_account("threadtask1/pthread_join12", now_ns() - __ta_t0_threadtask1_pthread_join12_70_20);
// TA_BEGIN: main1.c:71 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_free13_71_19 = now_ns();
    free(task_arg1); // 释放动态分配的内存    
// TA_END: main1.c:71 free
time_account("threadtask1/free13", now_ns() - __ta_t0_threadtask1_free13_71_19);
// TA_BEGIN: main1.c:72 insertsort
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_insertsort14_72_18 = now_ns();
    insertsort(arg);
// TA_END: main1.c:72 insertsort
time_account("threadtask1/insertsort14", now_ns() - __ta_t0_threadtask1_insertsort14_72_18);
// TA_BEGIN: main1.c:73 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf15_73_17 = now_ns();
    printf("task4结束\n");
// TA_END: main1.c:73 printf
time_account("threadtask1/printf15", now_ns() - __ta_t0_threadtask1_printf15_73_17);
    return NULL;
}
void threadtask5()
{
    int i = 0;
    while (i < 3)
    {
// TA_BEGIN: main1.c:81 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask5_while_printf1_81_16 = now_ns();
        printf("while循环测试\n");
// TA_END: main1.c:81 printf
time_account("threadtask5/while/printf1", now_ns() - __ta_t0_threadtask5_while_printf1_81_16);
        i++;
    }
    do
    {
// TA_BEGIN: main1.c:86 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask5_while_printf2_86_15 = now_ns();
        printf("do-while循环测试\n");
// TA_END: main1.c:86 printf
time_account("threadtask5/while/printf2", now_ns() - __ta_t0_threadtask5_while_printf2_86_15);
        i--;
    } while (i == 0);
    for (int i = 0; i < 5; i++)
    {
// TA_BEGIN: main1.c:91 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask5_while_printf3_91_14 = now_ns();
        printf("for循环测试\n");
// TA_END: main1.c:91 printf
time_account("threadtask5/while/printf3", now_ns() - __ta_t0_threadtask5_while_printf3_91_14);
    }
    int j = 2;
    switch (j)
    {
    case 1:
// TA_BEGIN: main1.c:97 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask5_switch0_printf4_97_13 = now_ns();
        printf("switch:1测试\n");
// TA_END: main1.c:97 printf
time_account("threadtask5/switch0/printf4", now_ns() - __ta_t0_threadtask5_switch0_printf4_97_13);
        break;
    case 2:
// TA_BEGIN: main1.c:100 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask5_printf5_100_12 = now_ns();
        printf("switch:2测试\n");
// TA_END: main1.c:100 printf
time_account("threadtask5/printf5", now_ns() - __ta_t0_threadtask5_printf5_100_12);
        break;
    default:
// TA_BEGIN: main1.c:103 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask5_while_printf6_103_11 = now_ns();
        printf("hello\n");
// TA_END: main1.c:103 printf
time_account("threadtask5/while/printf6", now_ns() - __ta_t0_threadtask5_while_printf6_103_11);
        break;
    }
}

int main() {
    //threadtask5();
// TA_BEGIN: main1.c:110 malloc
; /* TA_PAD */
uint64_t __ta_t0_main_while_malloc1_110_10 = now_ns();
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
// TA_END: main1.c:110 malloc
time_account("main/while/malloc1", now_ns() - __ta_t0_main_while_malloc1_110_10);
    if (task_arg == NULL) {
// TA_BEGIN: main1.c:112 fprintf
; /* TA_PAD */
uint64_t __ta_t0_main_fprintf2_112_9 = now_ns();
        fprintf(stderr, "内存分配失败\n");
// TA_END: main1.c:112 fprintf
time_account("main/fprintf2", now_ns() - __ta_t0_main_fprintf2_112_9);
        return 1;
    }
    *task_arg = 41; // 设置任务参数

    // 创建线程并绑定任务函数
    if ((__extension__({ uint64_t __ta_t0_main_while_pthread_create3_118_8 = now_ns(); __auto_type __ta_ret = pthread_create(&thread, NULL, threadtask1, task_arg); time_account("main/while/pthread_create3", now_ns() - __ta_t0_main_while_pthread_create3_118_8); __ta_ret; })) != 0) {
// TA_BEGIN: main1.c:119 fprintf
; /* TA_PAD */
uint64_t __ta_t0_main_fprintf4_119_7 = now_ns();
        fprintf(stderr, "线程创建失败\n");
// TA_END: main1.c:119 fprintf
time_account("main/fprintf4", now_ns() - __ta_t0_main_fprintf4_119_7);
// TA_BEGIN: main1.c:120 free
; /* TA_PAD */
uint64_t __ta_t0_main_free5_120_6 = now_ns();
        free(task_arg); // 如果线程创建失败，释放内存
// TA_END: main1.c:120 free
time_account("main/free5", now_ns() - __ta_t0_main_free5_120_6);
        return 1;
    }

    if ((__extension__({ uint64_t __ta_t0_main_while_pthread_join6_124_5 = now_ns(); __auto_type __ta_ret = pthread_join(thread, NULL); time_account("main/while/pthread_join6", now_ns() - __ta_t0_main_while_pthread_join6_124_5); __ta_ret; })) != 0) {
// TA_BEGIN: main1.c:125 fprintf
; /* TA_PAD */
uint64_t __ta_t0_main_fprintf7_125_4 = now_ns();
        fprintf(stderr, "等待线程完成失败\n");
// TA_END: main1.c:125 fprintf
time_account("main/fprintf7", now_ns() - __ta_t0_main_fprintf7_125_4);
// TA_BEGIN: main1.c:126 free
; /* TA_PAD */
uint64_t __ta_t0_main_free8_126_3 = now_ns();
        free(task_arg); // 确保释放内存
// TA_END: main1.c:126 free
time_account("main/free8", now_ns() - __ta_t0_main_free8_126_3);
        return 1;
    }

// TA_BEGIN: main1.c:130 free
; /* TA_PAD */
uint64_t __ta_t0_main_while_free9_130_2 = now_ns();
    free(task_arg); // 释放动态分配的内存
// TA_END: main1.c:130 free
time_account("main/while/free9", now_ns() - __ta_t0_main_while_free9_130_2);
// TA_BEGIN: main1.c:131 printf
; /* TA_PAD */
uint64_t __ta_t0_main_while_printf10_131_1 = now_ns();
    printf("主线程已完成\n");
// TA_END: main1.c:131 printf
time_account("main/while/printf10", now_ns() - __ta_t0_main_while_printf10_131_1);
    return 0;
}