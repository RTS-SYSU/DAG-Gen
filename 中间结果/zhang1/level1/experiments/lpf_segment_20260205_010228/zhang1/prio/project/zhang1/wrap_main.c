#include "prog_timer.h"

// Link-time main wrapper. Compile with: -Wl,--wrap=main
// Keeps original source unchanged while measuring total program time.

int __real_main(int argc, char **argv);

int __wrap_main(int argc, char **argv) {
    PROG_BEGIN();
    return __real_main(argc, argv);
}

