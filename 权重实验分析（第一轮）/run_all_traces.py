#!/usr/bin/env python3
"""
zhang2 六种调度策略 trace 对比工具
编译运行带 trace 的 C 程序，收集每个 MU 块的时间线
"""
import subprocess, os, sys, json, textwrap

BASE = "/home/firefly/Desktop/ScratchDAG/权重实验分析"
os.makedirs(BASE, exist_ok=True)

# zhang2 的 MU 块优先级映射 (从插桩代码提取)
# 格式: { algo: { "段名": prio } }
PRIO_MAP = {
    "zhao2020": {
        "c2:C1":88, "c2:C2":87, "c2:C3":86,
        "c1:C4":92, "c1:C5":96,
        "c0:C7":91,
        "main:C8":99, "main:C9":98, "main:C10":97,
        "main:C11":90, "main:C12":89,
        "main:C13":95, "main:C14":94, "main:C15":93,
    },
    "heft": {
        "c2:C1":94, "c2:C2":93, "c2:C3":89,
        "c1:C4":96, "c1:C5":95,
        "c0:C7":92,
        "main:C8":99, "main:C9":98, "main:C10":97,
        "main:C11":91, "main:C12":90,
        "main:C13":88, "main:C14":87, "main:C15":86,
    },
    "t_level": {
        "c2:C1":87, "c2:C2":92, "c2:C3":96,
        "c1:C4":88, "c1:C5":93,
        "c0:C7":89,
        "main:C8":86, "main:C9":90, "main:C10":91,
        "main:C11":94, "main:C12":95,
        "main:C13":97, "main:C14":98, "main:C15":99,
    },
    "wcet_first": {
        "c2:C1":88, "c2:C2":97, "c2:C3":98,
        "c1:C4":87, "c1:C5":99,
        "c0:C7":91,
        "main:C8":92, "main:C9":89, "main:C10":90,
        "main:C11":96, "main:C12":93,
        "main:C13":94, "main:C14":95, "main:C15":86,
    },
}

C_TEMPLATE = r"""
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
#ifdef USE_FIFO
  struct sched_param sp; sp.sched_priority = prio;
  pthread_setschedparam(pthread_self(), SCHED_FIFO, &sp);
#endif
  (void)prio;
}

/* ---- workers ---- */
static void *worker_c2(void *arg) {
  SET_PRIO_C2_1;
  TB(g_trace_c2,g_n_c2,"c2:C1=15");
  pthread_mutex_lock(&mutex_01); busy_wait_seconds(C1); pthread_mutex_unlock(&mutex_01);
  TE(g_trace_c2,g_n_c2);
  SET_PRIO_C2_2;
  sem_wait(&sem_02);
  TB(g_trace_c2,g_n_c2,"c2:C2=200");
  pthread_mutex_lock(&mutex_02); busy_wait_seconds(C2); pthread_mutex_unlock(&mutex_02);
  TE(g_trace_c2,g_n_c2);
  SET_PRIO_C2_3;
  sem_wait(&sem_03);
  TB(g_trace_c2,g_n_c2,"c2:C3=300");
  pthread_mutex_lock(&mutex_03); busy_wait_seconds(C3); pthread_mutex_unlock(&mutex_03);
  TE(g_trace_c2,g_n_c2);
  return NULL;
}
static void *worker_c1(void *arg) {
  SET_PRIO_C1_1;
  TB(g_trace_c1,g_n_c1,"c1:C4=15");
  pthread_mutex_lock(&mutex_04); busy_wait_seconds(C4); pthread_mutex_unlock(&mutex_04);
  TE(g_trace_c1,g_n_c1);
  SET_PRIO_C1_2;
  sem_wait(&sem_01);
  TB(g_trace_c1,g_n_c1,"c1:C5=400");
  pthread_mutex_lock(&mutex_05); busy_wait_seconds(C5); pthread_mutex_unlock(&mutex_05);
  TE(g_trace_c1,g_n_c1);
  return NULL;
}
static void *worker_c0(void *arg) {
  SET_PRIO_C0_1;
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

  SET_PRIO_MAIN_1;
  TB(g_trace_main,g_n_main,"main:C8=30");
  pthread_mutex_lock(&mutex_07); busy_wait_seconds(C8); pthread_mutex_unlock(&mutex_07);
  TE(g_trace_main,g_n_main);

  pthread_create(&thread_c0,NULL,worker_c0,NULL);
  pthread_create(&thread_c1,NULL,worker_c1,NULL);
  pthread_create(&thread_c2,NULL,worker_c2,NULL);

  SET_PRIO_MAIN_2;
  TB(g_trace_main,g_n_main,"main:C9=40");
  pthread_mutex_lock(&mutex_08); busy_wait_seconds(C9); pthread_mutex_unlock(&mutex_08);
  TE(g_trace_main,g_n_main);

  SET_PRIO_MAIN_3;
  TB(g_trace_main,g_n_main,"main:C10=50");
  pthread_mutex_lock(&mutex_09); busy_wait_seconds(C10); pthread_mutex_unlock(&mutex_09);
  TE(g_trace_main,g_n_main);

  sem_post(&sem_01); sem_post(&sem_02);

  SET_PRIO_MAIN_4;
  pthread_join(thread_c0,NULL);
  TB(g_trace_main,g_n_main,"main:C11=100");
  pthread_mutex_lock(&mutex_10); busy_wait_seconds(C11); pthread_mutex_unlock(&mutex_10);
  TE(g_trace_main,g_n_main);

  SET_PRIO_MAIN_5;
  TB(g_trace_main,g_n_main,"main:C12=50");
  pthread_mutex_lock(&mutex_11); busy_wait_seconds(C12); pthread_mutex_unlock(&mutex_11);
  TE(g_trace_main,g_n_main);

  sem_post(&sem_03);

  SET_PRIO_MAIN_6;
  pthread_join(thread_c1,NULL);
  TB(g_trace_main,g_n_main,"main:C13=80");
  pthread_mutex_lock(&mutex_12); busy_wait_seconds(C13); pthread_mutex_unlock(&mutex_12);
  TE(g_trace_main,g_n_main);

  SET_PRIO_MAIN_7;
  TB(g_trace_main,g_n_main,"main:C14=80");
  pthread_mutex_lock(&mutex_13); busy_wait_seconds(C14); pthread_mutex_unlock(&mutex_13);
  TE(g_trace_main,g_n_main);

  SET_PRIO_MAIN_8;
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
"""

def gen_c_source(algo):
    """生成带优先级设置的 C 源码"""
    src = C_TEMPLATE
    if algo == "CFS":
        # 所有 SET_PRIO 替换为空
        for tag in ["SET_PRIO_C2_1","SET_PRIO_C2_2","SET_PRIO_C2_3",
                     "SET_PRIO_C1_1","SET_PRIO_C1_2",
                     "SET_PRIO_C0_1",
                     "SET_PRIO_MAIN_1","SET_PRIO_MAIN_2","SET_PRIO_MAIN_3",
                     "SET_PRIO_MAIN_4","SET_PRIO_MAIN_5","SET_PRIO_MAIN_6",
                     "SET_PRIO_MAIN_7","SET_PRIO_MAIN_8"]:
            src = src.replace(tag + ";", "/* CFS: no prio */")
        return src
    elif algo == "FIFO":
        # FIFO: 所有线程同优先级 50
        for tag in ["SET_PRIO_C2_1","SET_PRIO_C2_2","SET_PRIO_C2_3",
                     "SET_PRIO_C1_1","SET_PRIO_C1_2",
                     "SET_PRIO_C0_1",
                     "SET_PRIO_MAIN_1","SET_PRIO_MAIN_2","SET_PRIO_MAIN_3",
                     "SET_PRIO_MAIN_4","SET_PRIO_MAIN_5","SET_PRIO_MAIN_6",
                     "SET_PRIO_MAIN_7","SET_PRIO_MAIN_8"]:
            src = src.replace(tag + ";", "set_fifo(50);")
        return src.replace("#ifdef USE_FIFO", "#if 1")
    else:
        pm = PRIO_MAP[algo]
        mapping = {
            "SET_PRIO_C2_1": pm["c2:C1"], "SET_PRIO_C2_2": pm["c2:C2"], "SET_PRIO_C2_3": pm["c2:C3"],
            "SET_PRIO_C1_1": pm["c1:C4"], "SET_PRIO_C1_2": pm["c1:C5"],
            "SET_PRIO_C0_1": pm["c0:C7"],
            "SET_PRIO_MAIN_1": pm["main:C8"], "SET_PRIO_MAIN_2": pm["main:C9"],
            "SET_PRIO_MAIN_3": pm["main:C10"], "SET_PRIO_MAIN_4": pm["main:C11"],
            "SET_PRIO_MAIN_5": pm["main:C12"], "SET_PRIO_MAIN_6": pm["main:C13"],
            "SET_PRIO_MAIN_7": pm["main:C14"], "SET_PRIO_MAIN_8": pm["main:C15"],
        }
        for tag, prio in mapping.items():
            src = src.replace(tag + ";", f"set_fifo({prio});")
        return src.replace("#ifdef USE_FIFO", "#if 1")

def compile_and_run(algo):
    cfile = os.path.join(BASE, f"zhang2_{algo}_trace.c")
    binary = os.path.join(BASE, f"zhang2_{algo}_trace")
    src = gen_c_source(algo)
    with open(cfile, "w") as f:
        f.write(src)
    # compile
    r = subprocess.run(
        ["gcc", "-O0", "-g", "-std=c11", "-pthread", "-DWORK_SCALE=100",
         cfile, "-o", binary, "-lm"],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[{algo}] compile error: {r.stderr}")
        return None
    # run (需要 sudo 才能设 SCHED_FIFO)
    if algo in ("CFS",):
        cmd = ["taskset", "-c", "6,7", binary]
    else:
        cmd = ["sudo", "taskset", "-c", "6,7", binary]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"[{algo}] run error: {r.stderr}")
        return None
    return r.stdout

def parse_trace(output):
    lines = []
    for line in output.strip().split("\n"):
        parts = line.split()
        if len(parts) == 4 and parts[0] not in ("TOTAL:",):
            try:
                lines.append({
                    "seg": parts[0],
                    "begin": float(parts[1]),
                    "end": float(parts[2]),
                    "dur": float(parts[3]),
                })
            except ValueError:
                pass
        elif line.startswith("TOTAL:"):
            total = float(line.split()[1])
            return lines, total
    return lines, 0

ALGOS = ["CFS", "FIFO", "zhao2020", "heft", "t_level", "wcet_first"]

results = {}
for algo in ALGOS:
    print(f"Running {algo}...")
    out = compile_and_run(algo)
    if out:
        traces, total = parse_trace(out)
        results[algo] = {"traces": traces, "total": total}
        print(f"  {algo}: {total:.1f} ms")

# 保存原始数据
with open(os.path.join(BASE, "zhang2_all_traces.json"), "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\nDone! Results saved to", BASE)
