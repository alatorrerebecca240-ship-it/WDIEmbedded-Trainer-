#include "student_average.h"

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
    const Student exact = {"Lin", {80, 90, 100}};
    const Student fraction = {"Qi", {80, 81, 81}};
    expect_near("exact", student_average(&exact), 90.0);
    expect_near("fraction", student_average(&fraction), 242.0 / 3.0);
    expect_near("null", student_average(NULL), 0.0);
    if (failures == 0) {
        puts("PASS student average");
    }
    return failures == 0 ? 0 : 1;
}
