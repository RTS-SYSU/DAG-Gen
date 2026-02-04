#include "prog_timer.h"

int __real_main(int argc, char **argv);

int __wrap_main(int argc, char **argv)
{
    PROG_BEGIN();
    int rc = __real_main(argc, argv);
    PROG_END();
    return rc;
}

