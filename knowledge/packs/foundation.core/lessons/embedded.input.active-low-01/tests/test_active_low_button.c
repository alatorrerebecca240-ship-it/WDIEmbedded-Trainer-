#include "active_low_button.h"

#include <stdio.h>

static int failures = 0;

static void expect_bool(const char *name, bool actual, bool expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %d, got %d\n", name, (int)expected, (int)actual);
        ++failures;
    }
}

int main(void)
{
    expect_bool("low pressed", active_low_pressed(0U), true);
    expect_bool("high released", active_low_pressed(1U), false);
    expect_bool("nonzero high", active_low_pressed(255U), false);
    if (failures == 0) {
        puts("PASS active low button");
    }
    return failures == 0 ? 0 : 1;
}
