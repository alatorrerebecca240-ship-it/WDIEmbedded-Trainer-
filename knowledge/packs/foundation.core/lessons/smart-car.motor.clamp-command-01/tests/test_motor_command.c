#include "motor_command.h"

#include <stdio.h>

static int failures = 0;

static void expect_equal(const char *name, int16_t actual, int16_t expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %d, got %d\n", name, (int)expected, (int)actual);
        ++failures;
    }
}

int main(void)
{
    expect_equal("inside positive", clamp_motor_command(350, 1000), 350);
    expect_equal("inside negative", clamp_motor_command(-350, 1000), -350);
    expect_equal("positive saturation", clamp_motor_command(5000, 1000), 1000);
    expect_equal("negative saturation", clamp_motor_command(-5000, 1000), -1000);
    expect_equal("zero limit", clamp_motor_command(42, 0), 0);
    expect_equal("maximum int32", clamp_motor_command(INT32_MAX, INT16_MAX), INT16_MAX);
    expect_equal("minimum int32", clamp_motor_command(INT32_MIN, INT16_MAX), -INT16_MAX);
    if (failures == 0) {
        puts("PASS motor command limit");
    }
    return failures == 0 ? 0 : 1;
}
