#pragma once

#include <stdint.h>

// Standalone segment tracing runtime for Level-1 instrumentation.
// Segment scopes are assumed NON-NESTED per thread (TLS single-slot).

#ifdef __cplusplus
extern "C" {
#endif

void segtrace_init(const char *out_dir);
void segtrace_begin(const char *seg_id);
void segtrace_end(const char *seg_id);

#ifdef __cplusplus
}
#endif

#define SEG_BEGIN(ID) segtrace_begin((ID))
#define SEG_END(ID) segtrace_end((ID))

