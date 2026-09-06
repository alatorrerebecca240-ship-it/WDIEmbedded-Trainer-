#include "sample_mean.h"

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
    const double positive[] = {1.0, 2.0, 6.0};
    const double centered[] = {-2.0, -1.0, 1.0, 2.0};
    const double one[] = {3.25};
    expect_near("positive", sample_mean(positive, 3U), 3.0);
    expect_near("centered", sample_mean(centered, 4U), 0.0);
    expect_near("single", sample_mean(one, 1U), 3.25);
    expect_near("empty", sample_mean(NULL, 0U), 0.0);
    if (failures == 0) {
        puts("PASS sample mean");
    }
    return failures == 0 ? 0 : 1;
}
