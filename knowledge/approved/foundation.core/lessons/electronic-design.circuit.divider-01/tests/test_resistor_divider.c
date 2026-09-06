#include "resistor_divider.h"

#include <math.h>
#include <stdio.h>

static int failures = 0;

static void expect_near(const char *name, double actual, double expected)
{
    if (!(fabs(actual - expected) <= 1e-9)) {
        fprintf(stderr, "FAIL %s: expected %.12g, got %.12g\n", name, expected, actual);
        ++failures;
    }
}

int main(void)
{
    expect_near("equal resistors", divider_output(5.0, 1000.0, 1000.0), 2.5);
    expect_near("one third", divider_output(12.0, 2000.0, 1000.0), 4.0);
    expect_near("zero bottom", divider_output(3.3, 1000.0, 0.0), 0.0);
    expect_near("negative invalid", divider_output(5.0, -1.0, 1000.0), 0.0);
    expect_near("zero total", divider_output(5.0, 0.0, 0.0), 0.0);
    if (failures == 0) {
        puts("PASS resistor divider");
    }
    return failures == 0 ? 0 : 1;
}
