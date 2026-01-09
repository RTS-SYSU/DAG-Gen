/*  multithread_demo_fix.c  */
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <semaphore.h>

/* -------- 宏参数 -------- */
#define BUF_SIZE            5
#define PRODUCER_COUNT      2
#define ITEMS_PER_PRODUCER  10
#define TOTAL_ITEMS  (PRODUCER_COUNT * ITEMS_PER_PRODUCER)

/* -------- 全局同步原语 -------- */
static sem_t           sem_empty;           /* 剩余空槽 */
static sem_t           sem_full;            /* 已填数据数 */
static pthread_mutex_t buf_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t  cond_done = PTHREAD_COND_INITIALIZER;

/* -------- 共享数据 -------- */
static int buffer[BUF_SIZE];
static int in = 0, out = 0;
static int produced_total = 0;
static int consumed_total = 0;
static int all_done = 0;

/* ========== 生产者线程 ========== */
void *producer(void *arg)
{
    long pid = (long)arg;                      /* 0 / 1 … */
    for (int i = 0; i < ITEMS_PER_PRODUCER; ++i) {
        int item = (int)(pid * 100 + i);       /* 待写入数据 */

        sem_wait(&sem_empty);                  /* -- 空槽 */
        pthread_mutex_lock(&buf_mutex);

        buffer[in] = item;
        in = (in + 1) % BUF_SIZE;
        ++produced_total;
        printf("[P%ld] produce %d   (total=%d)\n", pid, item, produced_total);

        pthread_mutex_unlock(&buf_mutex);
        sem_post(&sem_full);                   /* ++ 已填 */
    }
    return NULL;
}

/* ========== 消费者线程 ========== */
void *consumer(void *arg) 
{
    while (1) {
        sem_wait(&sem_full);                   /* -- 已填 */
        pthread_mutex_lock(&buf_mutex);

        int item = buffer[out];
        out = (out + 1) % BUF_SIZE;
        ++consumed_total;
        printf("                     [C] consume %d   (total=%d)\n",
               item, consumed_total);

        /* 若全部消费完毕，设置完成标志并广播 */
        if (consumed_total == TOTAL_ITEMS) {
            all_done = 1;
            pthread_cond_broadcast(&cond_done);  /* notifyAll */
            pthread_mutex_unlock(&buf_mutex);
            sem_post(&sem_empty);               /* 归还空槽 */
            break;                              /* 退出循环 */
        }

        pthread_mutex_unlock(&buf_mutex);
        sem_post(&sem_empty);                   /* ++ 空槽 */
    }
    return NULL;
}

/* ========== 监视线程：等待全部消费完成 ========== */
void *watcher(void *arg)
{
    pthread_mutex_lock(&buf_mutex);
    while (!all_done) {                         /* wait() 自动解锁再加锁 */
        pthread_cond_wait(&cond_done, &buf_mutex);
    }
    printf("\n[Watcher] All %d items have been PRODUCED & CONSUMED. ✅\n\n",
           TOTAL_ITEMS);
    pthread_mutex_unlock(&buf_mutex);
    return NULL;
}

/* ========== 主函数 ========== */
int main(void)
{
    pthread_t prod[PRODUCER_COUNT], cons, watch;

    sem_init(&sem_empty, 0, BUF_SIZE);
    sem_init(&sem_full,  0, 0);

    /* 启动消费者 & 监视线程 */
    pthread_create(&cons,  NULL, consumer, NULL);
    pthread_create(&watch, NULL, watcher,  NULL);

    /* 启动生产者 */
    for (long i = 0; i < PRODUCER_COUNT; ++i)
        pthread_create(&prod[i], NULL, producer, (void *)i);

    /* 等待所有线程结束 */
    for (int i = 0; i < PRODUCER_COUNT; ++i) pthread_join(prod[i], NULL);
    pthread_join(watch, NULL);
    pthread_join(cons,  NULL);

    /* 清理资源 */
    sem_destroy(&sem_empty);
    sem_destroy(&sem_full);
    pthread_mutex_destroy(&buf_mutex);
    pthread_cond_destroy(&cond_done);
    return 0;
}
