#pragma once

#include <stdint.h>

void l1_prog_begin(void);
void l1_prog_end(void);
uint64_t l1_prog_total_ns(void);

#define PROG_BEGIN() l1_prog_begin()
#define PROG_END() l1_prog_end()

