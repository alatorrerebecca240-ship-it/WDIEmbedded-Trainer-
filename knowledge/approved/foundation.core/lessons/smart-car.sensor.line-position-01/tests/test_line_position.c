#include "line_position.h"

#include <inttypes.h>
#include <stdio.h>

static int failures = 0;

static void expect_equal(const char *name, int32_t actual, int32_t expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %" PRId32 ", got %" PRId32 "\n", name, expected, actual);
        ++failures;
    }
}

int main(void)
{
    expect_equal("no signal", line_position_three(0U, 0U, 0U), 0);
    expect_equal("left", line_position_three(100U, 0U, 0U), -1000);
    expect_equal("center", line_position_three(0U, 100U, 0U), 0);
    expect_equal("right", line_position_three(0U, 0U, 100U), 1000);
    expect_equal("balanced", line_position_three(500U, 500U, 500U), 0);
    expect_equal("right weighted", line_position_three(100U, 100U, 300U), 400);
    expect_equal("left weighted", line_position_three(300U, 100U, 100U), -400);
    expect_equal("negative truncates toward zero", line_position_three(2U, 0U, 1U), -333);
    expect_equal("positive truncates toward zero", line_position_three(1U, 0U, 2U), 333);
    expect_equal("maximum left reading", line_position_three(UINT16_MAX, 0U, 0U), -1000);
    expect_equal("maximum balanced readings", line_position_three(UINT16_MAX, UINT16_MAX, UINT16_MAX), 0);
    if (failures == 0) {
        puts("PASS line position");
    }
    return failures == 0 ? 0 : 1;
}
