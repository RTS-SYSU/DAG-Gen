#define _GNU_SOURCE
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

/*
 * Laplace(phi=4) toy DAG (4 layers) for ScratchDAG / Level-1 Stage-1.
 *
 * Topology (layered diamond / grid-like dependency):
 *
 *   L1:          A1
 *                |
 *   L2:        B1  B2
 *              |\  /|
 *   L3:        C1 C2 C3
 *              | \/ |
 *   L4:        D1   D2
 *
 * Dependencies are enforced only by pthread_join in child threads:
 * - A1 -> B1, B2
 * - B1 -> C1, C2
 * - B2 -> C2, C3
 * - C1 -> D1
 * - C2 -> D1, D2
 * - C3 -> D2
 *
 * Style constraints (ScratchDAG-friendly):
 * - Each node is a distinct thread function and contains compute.
 * - No pthread_t arrays; explicit thread variables.
 * - create/join appear as plain statements (one per line).
 */

/* Per-node weights (seconds, scaled by WORK_SCALE in busy_wait_seconds). */
#define W_A1 6.0
#define W_B1 5.0
#define W_B2 5.0
#define W_C1 4.0
#define W_C2 7.0
#define W_C3 4.0
#define W_D1 6.0
#define W_D2 6.0

#ifndef WORK_SCALE
#define WORK_SCALE 25000
#endif

static void busy_wait_seconds(double seconds)
{
    volatile unsigned long long sink = 0;
    unsigned long long repeat = (unsigned long long)(seconds * (double)WORK_SCALE * 0.1);
    if (repeat < 1) repeat = 1;
    for (unsigned long long r = 0; r < repeat; ++r) {
        /* Simple arithmetic loop to keep it line-stable and portable. */
        sink += (r * 1315423911ULL) ^ (sink >> 3);
    }
    /* prevent optimizing away */
    if (sink == 0xdeadbeefULL) {
        fprintf(stderr, "sink=%llu\n", sink);
    }
}

static pthread_t tA1;
static pthread_t tB1;
static pthread_t tB2;
static pthread_t tC1;
static pthread_t tC2;
static pthread_t tC3;
static pthread_t tD1;
static pthread_t tD2;

static void *A1_fn(void *arg)
{
    (void)arg;
    busy_wait_seconds(W_A1);
    return NULL;
}

static void *B1_fn(void *arg)
{
    (void)arg;
    pthread_join(tA1, NULL);
    busy_wait_seconds(W_B1);
    return NULL;
}

static void *B2_fn(void *arg)
{
    (void)arg;
    pthread_join(tA1, NULL);
    busy_wait_seconds(W_B2);
    return NULL;
}

static void *C1_fn(void *arg)
{
    (void)arg;
    pthread_join(tB1, NULL);
    busy_wait_seconds(W_C1);
    return NULL;
}

static void *C2_fn(void *arg)
{
    (void)arg;
    pthread_join(tB1, NULL);
    pthread_join(tB2, NULL);
    busy_wait_seconds(W_C2);
    return NULL;
}

static void *C3_fn(void *arg)
{
    (void)arg;
    pthread_join(tB2, NULL);
    busy_wait_seconds(W_C3);
    return NULL;
}

static void *D1_fn(void *arg)
{
    (void)arg;
    pthread_join(tC1, NULL);
    pthread_join(tC2, NULL);
    busy_wait_seconds(W_D1);
    return NULL;
}

static void *D2_fn(void *arg)
{
    (void)arg;
    pthread_join(tC2, NULL);
    pthread_join(tC3, NULL);
    busy_wait_seconds(W_D2);
    return NULL;
}

int main(void)
{
    int rc = 0;

    rc = pthread_create(&tA1, NULL, A1_fn, NULL);
    if (rc != 0) return rc;

    rc = pthread_create(&tB1, NULL, B1_fn, NULL);
    if (rc != 0) return rc;
    rc = pthread_create(&tB2, NULL, B2_fn, NULL);
    if (rc != 0) return rc;

    rc = pthread_create(&tC1, NULL, C1_fn, NULL);
    if (rc != 0) return rc;
    rc = pthread_create(&tC2, NULL, C2_fn, NULL);
    if (rc != 0) return rc;
    rc = pthread_create(&tC3, NULL, C3_fn, NULL);
    if (rc != 0) return rc;

    rc = pthread_create(&tD1, NULL, D1_fn, NULL);
    if (rc != 0) return rc;
    rc = pthread_create(&tD2, NULL, D2_fn, NULL);
    if (rc != 0) return rc;

    pthread_join(tD1, NULL);
    pthread_join(tD2, NULL);
    return 0;
}

