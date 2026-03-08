#include "prog_timer.h"

// Link-time main wrapper. Compile with: -Wl,--wrap=main
// When using --wrap=main, all references to main are redirected to __wrap_main,
// and the original main is available as __real_main.

int __real_main(int argc, char **argv);

int __wrap_main(int argc, char **argv)
{
    PROG_BEGIN();
    int rc = __real_main(argc, argv);
    PROG_END();
    return rc;
}

