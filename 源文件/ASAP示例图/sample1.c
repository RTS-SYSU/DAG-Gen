#include <pthread.h>
#include <semaphore.h>

#define C1 16.0
#define C2 18.0
#define C3 260.0
#define C4 220.0

#ifndef WORK_SCALE
#define WORK_SCALE 100
#endif

static volatile double g_busy_sink = 0.0;

static sem_t s1;
static pthread_mutex_t m1 = PTHREAD_MUTEX_INITIALIZER;
static pthread_t thread_a;

static void compute(double seconds)
{
  int repeat_count = (int)(seconds * WORK_SCALE + 0.5);
  if (repeat_count < 1)
      repeat_count = 1;

  double x = 1.000001;
  double y = 0.999999;
  double z = 1.0000003;
  double acc = 0.0;

  for (int r = 0; r < repeat_count; ++r)
  {
      for (int i = 0; i < 512; ++i)
      {
          x = x * 1.0000001 + y * 0.9999999 + z * 0.0000001;
          y = y * 1.0000002 + z * 0.9999998 + x * 0.0000002;
          z = z * 1.0000003 + x * 0.9999997 + y * 0.0000003;
          acc += x * y + z;
      }
  }

  g_busy_sink += acc;
}








static void *thread_A(void *arg)
{
    sem_post(&s1);
    return NULL;
}

int main(void)
{
    pthread_create(&thread_a, NULL, thread_A, NULL);
    sem_wait(&s1);
    pthread_join(thread_a, NULL);
    pthread_mutex_lock(&m1);
    pthread_mutex_unlock(&m1);
    return 0;
}
