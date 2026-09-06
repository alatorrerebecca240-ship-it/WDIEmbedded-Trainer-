#include "signal_rms.h"

#include <math.h>
#include <stdio.h>

static int failures = 0;

static void expect_near(const char *name, double actual, double expected)
{
    if (fabs(actual - expected) > 1e-6) {
        fprintf(stderr, "FAIL %s: expected %.9f, got %.9f\n", name, expected, actual);
        ++failures;
    }
}

int main(void)
{
    const float pair[] = {3.0F, 4.0F};
    const float signed_values[] = {-2.0F, 2.0F, -2.0F, 2.0F};
    const float zeros[] = {0.0F, 0.0F, 0.0F};

    expect_near("3-4 pair", signal_rms(pair, 2U), sqrt(12.5));
    expect_near("signed values", signal_rms(signed_values, 4U), 2.0);
    expect_near("zeros", signal_rms(zeros, 3U), 0.0);
    expect_near("empty", signal_rms(zeros, 0U), 0.0);
    expect_near("null", signal_rms(NULL, 4U), 0.0);

    if (failures == 0) {
        puts("PASS signal rms");
    }
    return failures == 0 ? 0 : 1;
}

