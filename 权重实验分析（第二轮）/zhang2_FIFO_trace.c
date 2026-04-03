
#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define C1 15.0
#define C2 200.0
#define C3 300.0
#define C4 15.0
#define C5 400.0
#define C6 20.0
#define C7 50.0
#define C8 30.0
#define C9 40.0
#define C10 50.0
#define C11 100.0
#define C12 50.0
#define C13 80.0
#define C14 80.0
#define C15 5.0

#define MAT_N 64
#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

static double mat_a[MAT_N][MAT_N];
static double mat_b[MAT_N][MAT_N];
static double mat_c[MAT_N][MAT_N];
static volatile double g_busy_sink = 0.0;

static pthread_t thread_c0, thread_c1, thread_c2;
static sem_t sem_01, sem_02, sem_03;
static pthread_mutex_t mutex_01=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_02=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_03=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_04=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_05=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_06=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_07=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_08=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_09=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_10=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_11=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_12=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_13=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_14=PTHREAD_MUTEX_INITIALIZER;

static struct timespec g_t0;
#define MAX_TRACE 64
typedef struct { const char *seg; long begin_us; long end_us; } trace_rec;
static trace_rec g_trace_main[MAX_TRACE];
static trace_rec g_trace_c0[MAX_TRACE];
static trace_rec g_trace_c1[MAX_TRACE];
static trace_rec g_trace_c2[MAX_TRACE];
static int g_n_main=0, g_n_c0=0, g_n_c1=0, g_n_c2=0;

static long us_since_start(void) {
  struct timespec now;
  clock_gettime(CLOCK_MONOTONIC, &now);
  return (long)(now.tv_sec - g_t0.tv_sec)*1000000L
       + (long)(now.tv_nsec - g_t0.tv_nsec)/1000L;
}
#define TB(arr,n,name) do{(arr)[(n)].seg=(name);(arr)[(n)].begin_us=us_since_start();}while(0)
#define TE(arr,n) do{(arr)[(n)].end_us=us_since_start();(n)++;}while(0)

static void init_matrices(void) {
  for(int i=0;i<MAT_N;++i) for(int j=0;j<MAT_N;++j){
    mat_a[i][j]=(double)(i+j+1); mat_b[i][j]=(double)(i*2+j+3); mat_c[i][j]=0.0;
  }
}
static void busy_wait_seconds(double seconds) {
  int rc=(int)(seconds*WORK_SCALE+0.5); if(rc<1)rc=1;
  double x=1.000001,y=0.999999,z=1.0000003,acc=0.0;
  for(int r=0;r<rc;++r) for(int i=0;i<512;++i){
    x=x*1.0000001+y*0.9999999+z*0.0000001;
    y=y*1.0000002+z*0.9999998+x*0.0000002;
    z=z*1.0000003+x*0.9999997+y*0.0000003;
    acc+=x*y+z;
  }
  g_busy_sink+=acc; mat_c[0][0]=g_busy_sink;
}

static void set_fifo(int prio) {
#if 1
  struct sched_param sp; sp.sched_priority = prio;
  pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);
#endif
  (void)prio;
}

static void *worker_c2(void *arg) {
  set_fifo(50);
  TB(g_trace_c2,g_n_c2,"c2:C1=15");
  pthread_mutex_lock(&mutex_01); busy_wait_seconds(C1); pthread_mutex_unlock(&mutex_01);
  TE(g_trace_c2,g_n_c2);
  set_fifo(50);
  sem_wait(&sem_02);
  TB(g_trace_c2,g_n_c2,"c2:C2=200");
  pthread_mutex_lock(&mutex_02); busy_wait_seconds(C2); pthread_mutex_unlock(&mutex_02);
  TE(g_trace_c2,g_n_c2);
  set_fifo(50);
  sem_wait(&sem_03);
  TB(g_trace_c2,g_n_c2,"c2:C3=300");
  pthread_mutex_lock(&mutex_03); busy_wait_seconds(C3); pthread_mutex_unlock(&mutex_03);
  TE(g_trace_c2,g_n_c2);
  return NULL;
}
static void *worker_c1(void *arg) {
  set_fifo(50);
  TB(g_trace_c1,g_n_c1,"c1:C4=15");
  pthread_mutex_lock(&mutex_04); busy_wait_seconds(C4); pthread_mutex_unlock(&mutex_04);
  TE(g_trace_c1,g_n_c1);
  set_fifo(50);
  sem_wait(&sem_01);
  TB(g_trace_c1,g_n_c1,"c1:C5=400");
  pthread_mutex_lock(&mutex_05); busy_wait_seconds(C5); pthread_mutex_unlock(&mutex_05);
  TE(g_trace_c1,g_n_c1);
  return NULL;
}
static void *worker_c0(void *arg) {
  set_fifo(50);
  TB(g_trace_c0,g_n_c0,"c0:C7=50");
  pthread_mutex_lock(&mutex_06); busy_wait_seconds(C7); pthread_mutex_unlock(&mutex_06);
  TE(g_trace_c0,g_n_c0);
  return NULL;
}

int main(void) {
  cpu_set_t cs; CPU_ZERO(&cs); CPU_SET(6,&cs); CPU_SET(7,&cs);
  sched_setaffinity(0,sizeof(cs),&cs);
  init_matrices();
  sem_init(&sem_01,0,0); sem_init(&sem_02,0,0); sem_init(&sem_03,0,0);
  clock_gettime(CLOCK_MONOTONIC, &g_t0);

  set_fifo(50);
  TB(g_trace_main,g_n_main,"main:C8=30");
  pthread_mutex_lock(&mutex_07); busy_wait_seconds(C8); pthread_mutex_unlock(&mutex_07);
  TE(g_trace_main,g_n_main);

  pthread_create(&thread_c0,NULL,worker_c0,NULL);
  pthread_create(&thread_c1,NULL,worker_c1,NULL);
  pthread_create(&thread_c2,NULL,worker_c2,NULL);

  set_fifo(50);
  TB(g_trace_main,g_n_main,"main:C9=40");
  pthread_mutex_lock(&mutex_08); busy_wait_seconds(C9); pthread_mutex_unlock(&mutex_08);
  TE(g_trace_main,g_n_main);

  set_fifo(50);
  TB(g_trace_main,g_n_main,"main:C10=50");
  pthread_mutex_lock(&mutex_09); busy_wait_seconds(C10); pthread_mutex_unlock(&mutex_09);
  TE(g_trace_main,g_n_main);

  sem_post(&sem_01); sem_post(&sem_02);

  set_fifo(50);
  pthread_join(thread_c0,NULL);
  TB(g_trace_main,g_n_main,"main:C11=100");
  pthread_mutex_lock(&mutex_10); busy_wait_seconds(C11); pthread_mutex_unlock(&mutex_10);
  TE(g_trace_main,g_n_main);

  set_fifo(50);
  TB(g_trace_main,g_n_main,"main:C12=50");
  pthread_mutex_lock(&mutex_11); busy_wait_seconds(C12); pthread_mutex_unlock(&mutex_11);
  TE(g_trace_main,g_n_main);

  sem_post(&sem_03);

  set_fifo(50);
  pthread_join(thread_c1,NULL);
  TB(g_trace_main,g_n_main,"main:C13=80");
  pthread_mutex_lock(&mutex_12); busy_wait_seconds(C13); pthread_mutex_unlock(&mutex_12);
  TE(g_trace_main,g_n_main);

  set_fifo(50);
  TB(g_trace_main,g_n_main,"main:C14=80");
  pthread_mutex_lock(&mutex_13); busy_wait_seconds(C14); pthread_mutex_unlock(&mutex_13);
  TE(g_trace_main,g_n_main);

  set_fifo(50);
  pthread_join(thread_c2,NULL);
  TB(g_trace_main,g_n_main,"main:C15=5");
  pthread_mutex_lock(&mutex_14); busy_wait_seconds(C15); pthread_mutex_unlock(&mutex_14);
  TE(g_trace_main,g_n_main);

  long total_us = us_since_start();
  trace_rec *all[]={g_trace_main,g_trace_c0,g_trace_c1,g_trace_c2};
  int ns[]={g_n_main,g_n_c0,g_n_c1,g_n_c2};
  trace_rec flat[MAX_TRACE*4]; int tot=0;
  for(int a=0;a<4;a++) for(int i=0;i<ns[a];i++) flat[tot++]=all[a][i];
  for(int i=0;i<tot-1;i++) for(int j=i+1;j<tot;j++)
    if(flat[j].begin_us<flat[i].begin_us){trace_rec t=flat[i];flat[i]=flat[j];flat[j]=t;}
  for(int i=0;i<tot;i++)
    printf("%-20s %10.1f %10.1f %10.1f\n",
      flat[i].seg, flat[i].begin_us/1000.0, flat[i].end_us/1000.0,
      (flat[i].end_us-flat[i].begin_us)/1000.0);
  printf("TOTAL: %.1f\n", total_us/1000.0);
  return 0;
}
