```sh
源代码图

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
```
```sh

```
```sh
rtl图


Function:: thread_A
  symbol_ref:DI ("sem_post")             simple.c:53:5 -1

Function:: main
  symbol_ref:DI ("pthread_create")       simple.c:59:5 -1
  symbol_ref:DI ("sem_wait")             simple.c:60:5 -1
  symbol_ref:DI ("pthread_join")         simple.c:61:5 -1
  symbol_ref:DI ("pthread_mutex_lock")   simple.c:62:5 -1
  symbol_ref:DI ("pthread_mutex_unlock") simple.c:63:5 -1


```
```sh
数据结构图
thread_A [
sem_post[s1]
]
main [
pthread_create[thread_A]
sem_wait[s1]
pthread_join[thread_A]
pthread_mutex_lock[m1]
pthread_mutex_unlock[m1]
]

```