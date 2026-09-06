#include "safe_average.h"

#include <limits.h>
#include <math.h>
#include <stdio.h>

static int failures = 0;

static void expect_near(const char *name, double actual, double expected)
{
    if (fabs(actual - expected) > 1e-9) {
        fprintf(stderr, "FAIL %s: expected %.12g, got %.12g\n", name, expected, actual);
        ++failures;
    }
}

int main(void)
{
    const int values[] = {1, 2, 8};
    const int large[] = {INT_MAX, INT_MAX};
    expect_near("fraction", average_ints(values, 3U), 11.0 / 3.0);
    expect_near("large", average_ints(large, 2U), (double)INT_MAX);
    expect_near("empty", average_ints(NULL, 0U), 0.0);
    if (failures == 0) {
        puts("PASS safe average");
    }
    return failures == 0 ? 0 : 1;
}
