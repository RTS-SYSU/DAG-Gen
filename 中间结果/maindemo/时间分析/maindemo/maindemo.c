#include "time_stat.h"  // TA_INCLUDE
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include "include/task.h"

pthread_t thread, thread1, thread2, thread3;

void* threadtask3(void* arg) {
// TA_BEGIN: maindemo.c:9 rad2deg
; /* TA_PAD */
uint64_t __ta_t0_threadtask3_rad2deg1_9_47 = now_ns();
    rad2deg(arg);
// TA_END: maindemo.c:9 rad2deg
uint64_t __ta_t0_threadtask3_rad2deg1_9_47_dur = now_ns() - __ta_t0_threadtask3_rad2deg1_9_47;
time_account("threadtask3/rad2deg1", __ta_t0_threadtask3_rad2deg1_9_47_dur);
time_trace("threadtask3/rad2deg1", __ta_t0_threadtask3_rad2deg1_9_47, __ta_t0_threadtask3_rad2deg1_9_47_dur);
// TA_BEGIN: maindemo.c:10 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask3_printf2_10_46 = now_ns();
    printf("task8结束\n");
// TA_END: maindemo.c:10 printf
uint64_t __ta_t0_threadtask3_printf2_10_46_dur = now_ns() - __ta_t0_threadtask3_printf2_10_46;
time_account("threadtask3/printf2", __ta_t0_threadtask3_printf2_10_46_dur);
time_trace("threadtask3/printf2", __ta_t0_threadtask3_printf2_10_46, __ta_t0_threadtask3_printf2_10_46_dur);
    return NULL;
}
void* threadtask4(void* arg) {
// TA_BEGIN: maindemo.c:14 prime
; /* TA_PAD */
uint64_t __ta_t0_threadtask4_prime1_14_45 = now_ns();
    prime(arg);
// TA_END: maindemo.c:14 prime
uint64_t __ta_t0_threadtask4_prime1_14_45_dur = now_ns() - __ta_t0_threadtask4_prime1_14_45;
time_account("threadtask4/prime1", __ta_t0_threadtask4_prime1_14_45_dur);
time_trace("threadtask4/prime1", __ta_t0_threadtask4_prime1_14_45, __ta_t0_threadtask4_prime1_14_45_dur);
// TA_BEGIN: maindemo.c:15 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask4_printf2_15_44 = now_ns();
    printf("task9结束\n");
// TA_END: maindemo.c:15 printf
uint64_t __ta_t0_threadtask4_printf2_15_44_dur = now_ns() - __ta_t0_threadtask4_printf2_15_44;
time_account("threadtask4/printf2", __ta_t0_threadtask4_printf2_15_44_dur);
time_trace("threadtask4/printf2", __ta_t0_threadtask4_printf2_15_44, __ta_t0_threadtask4_printf2_15_44_dur);
    return NULL;
}
void* threadtask2(void* arg) {
// TA_BEGIN: maindemo.c:19 malloc
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_malloc1_19_43 = now_ns();
    int* task_arg1 = malloc(sizeof(int));
// TA_END: maindemo.c:19 malloc
uint64_t __ta_t0_threadtask2_malloc1_19_43_dur = now_ns() - __ta_t0_threadtask2_malloc1_19_43;
time_account("threadtask2/malloc1", __ta_t0_threadtask2_malloc1_19_43_dur);
time_trace("threadtask2/malloc1", __ta_t0_threadtask2_malloc1_19_43, __ta_t0_threadtask2_malloc1_19_43_dur);
// TA_BEGIN: maindemo.c:20 malloc
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_malloc2_20_42 = now_ns();
    int* task_arg2 = malloc(sizeof(int));
// TA_END: maindemo.c:20 malloc
uint64_t __ta_t0_threadtask2_malloc2_20_42_dur = now_ns() - __ta_t0_threadtask2_malloc2_20_42;
time_account("threadtask2/malloc2", __ta_t0_threadtask2_malloc2_20_42_dur);
time_trace("threadtask2/malloc2", __ta_t0_threadtask2_malloc2_20_42, __ta_t0_threadtask2_malloc2_20_42_dur);
    *task_arg1 = 43;
    *task_arg2 = 44;

// TA_BEGIN: maindemo.c:24 minver
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_minver3_24_41 = now_ns();
    minver(arg);
// TA_END: maindemo.c:24 minver
uint64_t __ta_t0_threadtask2_minver3_24_41_dur = now_ns() - __ta_t0_threadtask2_minver3_24_41;
time_account("threadtask2/minver3", __ta_t0_threadtask2_minver3_24_41_dur);
time_trace("threadtask2/minver3", __ta_t0_threadtask2_minver3_24_41, __ta_t0_threadtask2_minver3_24_41_dur);
// TA_BEGIN: maindemo.c:25 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_printf4_25_40 = now_ns();
    printf("task5结束\n");
// TA_END: maindemo.c:25 printf
uint64_t __ta_t0_threadtask2_printf4_25_40_dur = now_ns() - __ta_t0_threadtask2_printf4_25_40;
time_account("threadtask2/printf4", __ta_t0_threadtask2_printf4_25_40_dur);
time_trace("threadtask2/printf4", __ta_t0_threadtask2_printf4_25_40, __ta_t0_threadtask2_printf4_25_40_dur);

    if ((__extension__({ uint64_t __ta_t0_threadtask2_pthread_create5_27_39 = now_ns(); __auto_type __ta_ret = pthread_create(&thread2, NULL, threadtask3, task_arg1); uint64_t __ta_t0_threadtask2_pthread_create5_27_39_dur = now_ns() - __ta_t0_threadtask2_pthread_create5_27_39; time_account("threadtask2/pthread_create5", __ta_t0_threadtask2_pthread_create5_27_39_dur); time_trace("threadtask2/pthread_create5", __ta_t0_threadtask2_pthread_create5_27_39, __ta_t0_threadtask2_pthread_create5_27_39_dur); __ta_ret; })) != 0) {
// TA_BEGIN: maindemo.c:28 fprintf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_if_fprintf6_28_38 = now_ns();
        fprintf(stderr, "线程创建失败\n");
// TA_END: maindemo.c:28 fprintf
uint64_t __ta_t0_threadtask2_if_fprintf6_28_38_dur = now_ns() - __ta_t0_threadtask2_if_fprintf6_28_38;
time_account("threadtask2/if/fprintf6", __ta_t0_threadtask2_if_fprintf6_28_38_dur);
time_trace("threadtask2/if/fprintf6", __ta_t0_threadtask2_if_fprintf6_28_38, __ta_t0_threadtask2_if_fprintf6_28_38_dur);
// TA_BEGIN: maindemo.c:29 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_if_free7_29_37 = now_ns();
        free(task_arg1); // 如果线程创建失败，释放内存
// TA_END: maindemo.c:29 free
uint64_t __ta_t0_threadtask2_if_free7_29_37_dur = now_ns() - __ta_t0_threadtask2_if_free7_29_37;
time_account("threadtask2/if/free7", __ta_t0_threadtask2_if_free7_29_37_dur);
time_trace("threadtask2/if/free7", __ta_t0_threadtask2_if_free7_29_37, __ta_t0_threadtask2_if_free7_29_37_dur);
        return NULL;
    }
    
    if ((__extension__({ uint64_t __ta_t0_threadtask2_pthread_create8_33_36 = now_ns(); __auto_type __ta_ret = pthread_create(&thread3, NULL, threadtask4, task_arg2); uint64_t __ta_t0_threadtask2_pthread_create8_33_36_dur = now_ns() - __ta_t0_threadtask2_pthread_create8_33_36; time_account("threadtask2/pthread_create8", __ta_t0_threadtask2_pthread_create8_33_36_dur); time_trace("threadtask2/pthread_create8", __ta_t0_threadtask2_pthread_create8_33_36, __ta_t0_threadtask2_pthread_create8_33_36_dur); __ta_ret; })) != 0) {
// TA_BEGIN: maindemo.c:34 fprintf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_if_fprintf9_34_35 = now_ns();
        fprintf(stderr, "线程创建失败\n");
// TA_END: maindemo.c:34 fprintf
uint64_t __ta_t0_threadtask2_if_fprintf9_34_35_dur = now_ns() - __ta_t0_threadtask2_if_fprintf9_34_35;
time_account("threadtask2/if/fprintf9", __ta_t0_threadtask2_if_fprintf9_34_35_dur);
time_trace("threadtask2/if/fprintf9", __ta_t0_threadtask2_if_fprintf9_34_35, __ta_t0_threadtask2_if_fprintf9_34_35_dur);
// TA_BEGIN: maindemo.c:35 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_if_free10_35_34 = now_ns();
        free(task_arg1); // 如果线程创建失败，释放内存
// TA_END: maindemo.c:35 free
uint64_t __ta_t0_threadtask2_if_free10_35_34_dur = now_ns() - __ta_t0_threadtask2_if_free10_35_34;
time_account("threadtask2/if/free10", __ta_t0_threadtask2_if_free10_35_34_dur);
time_trace("threadtask2/if/free10", __ta_t0_threadtask2_if_free10_35_34, __ta_t0_threadtask2_if_free10_35_34_dur);
        return NULL;
    }
// TA_BEGIN: maindemo.c:38 ndes
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_ndes11_38_33 = now_ns();
    ndes(arg);
// TA_END: maindemo.c:38 ndes
uint64_t __ta_t0_threadtask2_ndes11_38_33_dur = now_ns() - __ta_t0_threadtask2_ndes11_38_33;
time_account("threadtask2/ndes11", __ta_t0_threadtask2_ndes11_38_33_dur);
time_trace("threadtask2/ndes11", __ta_t0_threadtask2_ndes11_38_33, __ta_t0_threadtask2_ndes11_38_33_dur);
// TA_BEGIN: maindemo.c:39 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_printf12_39_32 = now_ns();
    printf("task6结束\n");
// TA_END: maindemo.c:39 printf
uint64_t __ta_t0_threadtask2_printf12_39_32_dur = now_ns() - __ta_t0_threadtask2_printf12_39_32;
time_account("threadtask2/printf12", __ta_t0_threadtask2_printf12_39_32_dur);
time_trace("threadtask2/printf12", __ta_t0_threadtask2_printf12_39_32, __ta_t0_threadtask2_printf12_39_32_dur);
// TA_BEGIN: maindemo.c:40 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_pthread_join13_40_31 = now_ns();
    pthread_join(thread2, NULL);
// TA_END: maindemo.c:40 pthread_join
uint64_t __ta_t0_threadtask2_pthread_join13_40_31_dur = now_ns() - __ta_t0_threadtask2_pthread_join13_40_31;
time_account("threadtask2/pthread_join13", __ta_t0_threadtask2_pthread_join13_40_31_dur);
time_trace("threadtask2/pthread_join13", __ta_t0_threadtask2_pthread_join13_40_31, __ta_t0_threadtask2_pthread_join13_40_31_dur);
// TA_BEGIN: maindemo.c:41 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_pthread_join14_41_30 = now_ns();
    pthread_join(thread3, NULL);
// TA_END: maindemo.c:41 pthread_join
uint64_t __ta_t0_threadtask2_pthread_join14_41_30_dur = now_ns() - __ta_t0_threadtask2_pthread_join14_41_30;
time_account("threadtask2/pthread_join14", __ta_t0_threadtask2_pthread_join14_41_30_dur);
time_trace("threadtask2/pthread_join14", __ta_t0_threadtask2_pthread_join14_41_30, __ta_t0_threadtask2_pthread_join14_41_30_dur);
// TA_BEGIN: maindemo.c:42 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_free15_42_29 = now_ns();
    free(task_arg1); // 释放动态分配的内存
// TA_END: maindemo.c:42 free
uint64_t __ta_t0_threadtask2_free15_42_29_dur = now_ns() - __ta_t0_threadtask2_free15_42_29;
time_account("threadtask2/free15", __ta_t0_threadtask2_free15_42_29_dur);
time_trace("threadtask2/free15", __ta_t0_threadtask2_free15_42_29, __ta_t0_threadtask2_free15_42_29_dur);
// TA_BEGIN: maindemo.c:43 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_free16_43_28 = now_ns();
    free(task_arg2); // 释放动态分配的内存
// TA_END: maindemo.c:43 free
uint64_t __ta_t0_threadtask2_free16_43_28_dur = now_ns() - __ta_t0_threadtask2_free16_43_28;
time_account("threadtask2/free16", __ta_t0_threadtask2_free16_43_28_dur);
time_trace("threadtask2/free16", __ta_t0_threadtask2_free16_43_28, __ta_t0_threadtask2_free16_43_28_dur);
// TA_BEGIN: maindemo.c:44 ludcmp
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_ludcmp17_44_27 = now_ns();
    ludcmp(arg);
// TA_END: maindemo.c:44 ludcmp
uint64_t __ta_t0_threadtask2_ludcmp17_44_27_dur = now_ns() - __ta_t0_threadtask2_ludcmp17_44_27;
time_account("threadtask2/ludcmp17", __ta_t0_threadtask2_ludcmp17_44_27_dur);
time_trace("threadtask2/ludcmp17", __ta_t0_threadtask2_ludcmp17_44_27, __ta_t0_threadtask2_ludcmp17_44_27_dur);
// TA_BEGIN: maindemo.c:45 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask2_printf18_45_26 = now_ns();
    printf("task7结束\n");
// TA_END: maindemo.c:45 printf
uint64_t __ta_t0_threadtask2_printf18_45_26_dur = now_ns() - __ta_t0_threadtask2_printf18_45_26;
time_account("threadtask2/printf18", __ta_t0_threadtask2_printf18_45_26_dur);
time_trace("threadtask2/printf18", __ta_t0_threadtask2_printf18_45_26, __ta_t0_threadtask2_printf18_45_26_dur);

    return NULL;
}
void* threadtask1(void* arg) {
// TA_BEGIN: maindemo.c:50 malloc
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_malloc1_50_25 = now_ns();
    int* task_arg1 = malloc(sizeof(int));
// TA_END: maindemo.c:50 malloc
uint64_t __ta_t0_threadtask1_malloc1_50_25_dur = now_ns() - __ta_t0_threadtask1_malloc1_50_25;
time_account("threadtask1/malloc1", __ta_t0_threadtask1_malloc1_50_25_dur);
time_trace("threadtask1/malloc1", __ta_t0_threadtask1_malloc1_50_25, __ta_t0_threadtask1_malloc1_50_25_dur);
    if (task_arg1 == NULL) {
// TA_BEGIN: maindemo.c:52 fprintf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_if_fprintf2_52_24 = now_ns();
        fprintf(stderr, "内存分配失败\n");
// TA_END: maindemo.c:52 fprintf
uint64_t __ta_t0_threadtask1_if_fprintf2_52_24_dur = now_ns() - __ta_t0_threadtask1_if_fprintf2_52_24;
time_account("threadtask1/if/fprintf2", __ta_t0_threadtask1_if_fprintf2_52_24_dur);
time_trace("threadtask1/if/fprintf2", __ta_t0_threadtask1_if_fprintf2_52_24, __ta_t0_threadtask1_if_fprintf2_52_24_dur);
        return NULL;
    }
    *task_arg1 = 42;

// TA_BEGIN: maindemo.c:57 Deg2rad
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_Deg2rad3_57_23 = now_ns();
    Deg2rad(arg);
// TA_END: maindemo.c:57 Deg2rad
uint64_t __ta_t0_threadtask1_Deg2rad3_57_23_dur = now_ns() - __ta_t0_threadtask1_Deg2rad3_57_23;
time_account("threadtask1/Deg2rad3", __ta_t0_threadtask1_Deg2rad3_57_23_dur);
time_trace("threadtask1/Deg2rad3", __ta_t0_threadtask1_Deg2rad3_57_23, __ta_t0_threadtask1_Deg2rad3_57_23_dur);
// TA_BEGIN: maindemo.c:58 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf4_58_22 = now_ns();
    printf("task1结束\n");
// TA_END: maindemo.c:58 printf
uint64_t __ta_t0_threadtask1_printf4_58_22_dur = now_ns() - __ta_t0_threadtask1_printf4_58_22;
time_account("threadtask1/printf4", __ta_t0_threadtask1_printf4_58_22_dur);
time_trace("threadtask1/printf4", __ta_t0_threadtask1_printf4_58_22, __ta_t0_threadtask1_printf4_58_22_dur);

    if ((__extension__({ uint64_t __ta_t0_threadtask1_pthread_create5_60_21 = now_ns(); __auto_type __ta_ret = pthread_create(&thread1, NULL,threadtask2, task_arg1); uint64_t __ta_t0_threadtask1_pthread_create5_60_21_dur = now_ns() - __ta_t0_threadtask1_pthread_create5_60_21; time_account("threadtask1/pthread_create5", __ta_t0_threadtask1_pthread_create5_60_21_dur); time_trace("threadtask1/pthread_create5", __ta_t0_threadtask1_pthread_create5_60_21, __ta_t0_threadtask1_pthread_create5_60_21_dur); __ta_ret; })) != 0) {
// TA_BEGIN: maindemo.c:61 fprintf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_if_fprintf6_61_20 = now_ns();
        fprintf(stderr, "线程创建失败\n");
// TA_END: maindemo.c:61 fprintf
uint64_t __ta_t0_threadtask1_if_fprintf6_61_20_dur = now_ns() - __ta_t0_threadtask1_if_fprintf6_61_20;
time_account("threadtask1/if/fprintf6", __ta_t0_threadtask1_if_fprintf6_61_20_dur);
time_trace("threadtask1/if/fprintf6", __ta_t0_threadtask1_if_fprintf6_61_20, __ta_t0_threadtask1_if_fprintf6_61_20_dur);
// TA_BEGIN: maindemo.c:62 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_if_free7_62_19 = now_ns();
        free(task_arg1); // 如果线程创建失败，释放内存
// TA_END: maindemo.c:62 free
uint64_t __ta_t0_threadtask1_if_free7_62_19_dur = now_ns() - __ta_t0_threadtask1_if_free7_62_19;
time_account("threadtask1/if/free7", __ta_t0_threadtask1_if_free7_62_19_dur);
time_trace("threadtask1/if/free7", __ta_t0_threadtask1_if_free7_62_19, __ta_t0_threadtask1_if_free7_62_19_dur);
        return NULL;
    }

// TA_BEGIN: maindemo.c:66 cover
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_cover8_66_18 = now_ns();
    cover(arg);
// TA_END: maindemo.c:66 cover
uint64_t __ta_t0_threadtask1_cover8_66_18_dur = now_ns() - __ta_t0_threadtask1_cover8_66_18;
time_account("threadtask1/cover8", __ta_t0_threadtask1_cover8_66_18_dur);
time_trace("threadtask1/cover8", __ta_t0_threadtask1_cover8_66_18, __ta_t0_threadtask1_cover8_66_18_dur);
// TA_BEGIN: maindemo.c:67 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf9_67_17 = now_ns();
    printf("task2结束\n");
// TA_END: maindemo.c:67 printf
uint64_t __ta_t0_threadtask1_printf9_67_17_dur = now_ns() - __ta_t0_threadtask1_printf9_67_17;
time_account("threadtask1/printf9", __ta_t0_threadtask1_printf9_67_17_dur);
time_trace("threadtask1/printf9", __ta_t0_threadtask1_printf9_67_17, __ta_t0_threadtask1_printf9_67_17_dur);
// TA_BEGIN: maindemo.c:68 duff
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_duff10_68_16 = now_ns();
    duff(arg);
// TA_END: maindemo.c:68 duff
uint64_t __ta_t0_threadtask1_duff10_68_16_dur = now_ns() - __ta_t0_threadtask1_duff10_68_16;
time_account("threadtask1/duff10", __ta_t0_threadtask1_duff10_68_16_dur);
time_trace("threadtask1/duff10", __ta_t0_threadtask1_duff10_68_16, __ta_t0_threadtask1_duff10_68_16_dur);
// TA_BEGIN: maindemo.c:69 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf11_69_15 = now_ns();
    printf("task3结束\n");
// TA_END: maindemo.c:69 printf
uint64_t __ta_t0_threadtask1_printf11_69_15_dur = now_ns() - __ta_t0_threadtask1_printf11_69_15;
time_account("threadtask1/printf11", __ta_t0_threadtask1_printf11_69_15_dur);
time_trace("threadtask1/printf11", __ta_t0_threadtask1_printf11_69_15, __ta_t0_threadtask1_printf11_69_15_dur);
// TA_BEGIN: maindemo.c:70 pthread_join
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_pthread_join12_70_14 = now_ns();
    pthread_join(thread1, NULL);
// TA_END: maindemo.c:70 pthread_join
uint64_t __ta_t0_threadtask1_pthread_join12_70_14_dur = now_ns() - __ta_t0_threadtask1_pthread_join12_70_14;
time_account("threadtask1/pthread_join12", __ta_t0_threadtask1_pthread_join12_70_14_dur);
time_trace("threadtask1/pthread_join12", __ta_t0_threadtask1_pthread_join12_70_14, __ta_t0_threadtask1_pthread_join12_70_14_dur);
// TA_BEGIN: maindemo.c:71 free
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_free13_71_13 = now_ns();
    free(task_arg1); // 释放动态分配的内存    
// TA_END: maindemo.c:71 free
uint64_t __ta_t0_threadtask1_free13_71_13_dur = now_ns() - __ta_t0_threadtask1_free13_71_13;
time_account("threadtask1/free13", __ta_t0_threadtask1_free13_71_13_dur);
time_trace("threadtask1/free13", __ta_t0_threadtask1_free13_71_13, __ta_t0_threadtask1_free13_71_13_dur);
// TA_BEGIN: maindemo.c:72 insertsort
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_insertsort14_72_12 = now_ns();
    insertsort(arg);
// TA_END: maindemo.c:72 insertsort
uint64_t __ta_t0_threadtask1_insertsort14_72_12_dur = now_ns() - __ta_t0_threadtask1_insertsort14_72_12;
time_account("threadtask1/insertsort14", __ta_t0_threadtask1_insertsort14_72_12_dur);
time_trace("threadtask1/insertsort14", __ta_t0_threadtask1_insertsort14_72_12, __ta_t0_threadtask1_insertsort14_72_12_dur);
// TA_BEGIN: maindemo.c:73 printf
; /* TA_PAD */
uint64_t __ta_t0_threadtask1_printf15_73_11 = now_ns();
    printf("task4结束\n");
// TA_END: maindemo.c:73 printf
uint64_t __ta_t0_threadtask1_printf15_73_11_dur = now_ns() - __ta_t0_threadtask1_printf15_73_11;
time_account("threadtask1/printf15", __ta_t0_threadtask1_printf15_73_11_dur);
time_trace("threadtask1/printf15", __ta_t0_threadtask1_printf15_73_11, __ta_t0_threadtask1_printf15_73_11_dur);
    return NULL;
}


int main() {

// TA_BEGIN: maindemo.c:80 malloc
; /* TA_PAD */
uint64_t __ta_t0_main_malloc1_80_10 = now_ns();
    int* task_arg = malloc(sizeof(int)); // 动态分配内存给任务参数
// TA_END: maindemo.c:80 malloc
uint64_t __ta_t0_main_malloc1_80_10_dur = now_ns() - __ta_t0_main_malloc1_80_10;
time_account("main/malloc1", __ta_t0_main_malloc1_80_10_dur);
time_trace("main/malloc1", __ta_t0_main_malloc1_80_10, __ta_t0_main_malloc1_80_10_dur);
    if (task_arg == NULL) {
// TA_BEGIN: maindemo.c:82 fprintf
; /* TA_PAD */
uint64_t __ta_t0_main_if_fprintf2_82_9 = now_ns();
        fprintf(stderr, "内存分配失败\n");
// TA_END: maindemo.c:82 fprintf
uint64_t __ta_t0_main_if_fprintf2_82_9_dur = now_ns() - __ta_t0_main_if_fprintf2_82_9;
time_account("main/if/fprintf2", __ta_t0_main_if_fprintf2_82_9_dur);
time_trace("main/if/fprintf2", __ta_t0_main_if_fprintf2_82_9, __ta_t0_main_if_fprintf2_82_9_dur);
        return 1;
    }
    *task_arg = 41; // 设置任务参数

    // 创建线程并绑定任务函数
    if ((__extension__({ uint64_t __ta_t0_main_pthread_create3_88_8 = now_ns(); __auto_type __ta_ret = pthread_create(&thread, NULL, threadtask1, task_arg); uint64_t __ta_t0_main_pthread_create3_88_8_dur = now_ns() - __ta_t0_main_pthread_create3_88_8; time_account("main/pthread_create3", __ta_t0_main_pthread_create3_88_8_dur); time_trace("main/pthread_create3", __ta_t0_main_pthread_create3_88_8, __ta_t0_main_pthread_create3_88_8_dur); __ta_ret; })) != 0) {
// TA_BEGIN: maindemo.c:89 fprintf
; /* TA_PAD */
uint64_t __ta_t0_main_if_fprintf4_89_7 = now_ns();
        fprintf(stderr, "线程创建失败\n");
// TA_END: maindemo.c:89 fprintf
uint64_t __ta_t0_main_if_fprintf4_89_7_dur = now_ns() - __ta_t0_main_if_fprintf4_89_7;
time_account("main/if/fprintf4", __ta_t0_main_if_fprintf4_89_7_dur);
time_trace("main/if/fprintf4", __ta_t0_main_if_fprintf4_89_7, __ta_t0_main_if_fprintf4_89_7_dur);
// TA_BEGIN: maindemo.c:90 free
; /* TA_PAD */
uint64_t __ta_t0_main_if_free5_90_6 = now_ns();
        free(task_arg); // 如果线程创建失败，释放内存
// TA_END: maindemo.c:90 free
uint64_t __ta_t0_main_if_free5_90_6_dur = now_ns() - __ta_t0_main_if_free5_90_6;
time_account("main/if/free5", __ta_t0_main_if_free5_90_6_dur);
time_trace("main/if/free5", __ta_t0_main_if_free5_90_6, __ta_t0_main_if_free5_90_6_dur);
        return 1;
    }

    if ((__extension__({ uint64_t __ta_t0_main_pthread_join6_94_5 = now_ns(); __auto_type __ta_ret = pthread_join(thread, NULL); uint64_t __ta_t0_main_pthread_join6_94_5_dur = now_ns() - __ta_t0_main_pthread_join6_94_5; time_account("main/pthread_join6", __ta_t0_main_pthread_join6_94_5_dur); time_trace("main/pthread_join6", __ta_t0_main_pthread_join6_94_5, __ta_t0_main_pthread_join6_94_5_dur); __ta_ret; })) != 0) {
// TA_BEGIN: maindemo.c:95 fprintf
; /* TA_PAD */
uint64_t __ta_t0_main_if_fprintf7_95_4 = now_ns();
        fprintf(stderr, "等待线程完成失败\n");
// TA_END: maindemo.c:95 fprintf
uint64_t __ta_t0_main_if_fprintf7_95_4_dur = now_ns() - __ta_t0_main_if_fprintf7_95_4;
time_account("main/if/fprintf7", __ta_t0_main_if_fprintf7_95_4_dur);
time_trace("main/if/fprintf7", __ta_t0_main_if_fprintf7_95_4, __ta_t0_main_if_fprintf7_95_4_dur);
// TA_BEGIN: maindemo.c:96 free
; /* TA_PAD */
uint64_t __ta_t0_main_if_free8_96_3 = now_ns();
        free(task_arg); // 确保释放内存
// TA_END: maindemo.c:96 free
uint64_t __ta_t0_main_if_free8_96_3_dur = now_ns() - __ta_t0_main_if_free8_96_3;
time_account("main/if/free8", __ta_t0_main_if_free8_96_3_dur);
time_trace("main/if/free8", __ta_t0_main_if_free8_96_3, __ta_t0_main_if_free8_96_3_dur);
        return 1;
    }

// TA_BEGIN: maindemo.c:100 free
; /* TA_PAD */
uint64_t __ta_t0_main_free9_100_2 = now_ns();
    free(task_arg); // 释放动态分配的内存
// TA_END: maindemo.c:100 free
uint64_t __ta_t0_main_free9_100_2_dur = now_ns() - __ta_t0_main_free9_100_2;
time_account("main/free9", __ta_t0_main_free9_100_2_dur);
time_trace("main/free9", __ta_t0_main_free9_100_2, __ta_t0_main_free9_100_2_dur);
// TA_BEGIN: maindemo.c:101 printf
; /* TA_PAD */
uint64_t __ta_t0_main_printf10_101_1 = now_ns();
    printf("主线程已完成\n");
// TA_END: maindemo.c:101 printf
uint64_t __ta_t0_main_printf10_101_1_dur = now_ns() - __ta_t0_main_printf10_101_1;
time_account("main/printf10", __ta_t0_main_printf10_101_1_dur);
time_trace("main/printf10", __ta_t0_main_printf10_101_1, __ta_t0_main_printf10_101_1_dur);
    return 0;
}