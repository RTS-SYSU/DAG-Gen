#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void l1_prog_begin(void);
void l1_prog_end(void);

#ifdef __cplusplus
}
#endif

#define PROG_BEGIN() l1_prog_begin()
#define PROG_END() l1_prog_end()

