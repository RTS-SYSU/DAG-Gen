```sh
源代码图

static void *thread_A(void *arg)
{
    (void)arg;
    compute(C3);
    sem_post(&s1);
    compute(C4);
    return NULL;
}

int main(void)
{
    sem_init(&s1, 0, 0);
    compute(C1);
    pthread_create(&thread_a, NULL, thread_A, NULL);
    sem_wait(&s1);
    compute(C2);
    pthread_join(thread_a, NULL);
    pthread_mutex_lock(&m1);
    compute(C2);
    pthread_mutex_unlock(&m1);
    sem_destroy(&s1);
    return 0;
}
```
```sh
rtl图

Function:: main
call_insn   symbol_ref   sem_init  simple.c:55:5 -1
call_insn   symbol_ref   compute  simple.c:56:5 -1
call_insn   symbol_ref   pthread_create  simple.c:57:5 -1
call_insn   symbol_ref   sem_wait  simple.c:58:5 -1
call_insn   symbol_ref   compute  simple.c:59:5 -1
call_insn   symbol_ref   pthread_join  simple.c:60:5 -1
call_insn   symbol_ref   pthread_mutex_lock  simple.c:61:5 -1
call_insn   symbol_ref   compute  simple.c:62:5 -1
call_insn   symbol_ref   pthread_mutex_unlock  simple.c:63:5 -1
call_insn   symbol_ref   sem_destroy  simple.c:64:5 -1
```
```sh
数据结构图
main [
sem_init
compute
pthread_create[thread_A]
sem_wait[s1]
compute
pthread_join[thread_A]
pthread_mutex_lock[m1]
compute   
pthread_mutex_unlock[m1]
sem_destroy
]

```