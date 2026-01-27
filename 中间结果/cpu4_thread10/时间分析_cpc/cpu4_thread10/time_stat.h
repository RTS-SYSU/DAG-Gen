#ifndef TIME_STAT_H
#define TIME_STAT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

uint64_t now_ns(void);
void time_account(const char* key, uint64_t dur_ns);
void time_trace(const char* key, uint64_t start_ns, uint64_t dur_ns);
void ta_set_priority(int prio);

#ifdef __cplusplus
}
#endif

#endif
