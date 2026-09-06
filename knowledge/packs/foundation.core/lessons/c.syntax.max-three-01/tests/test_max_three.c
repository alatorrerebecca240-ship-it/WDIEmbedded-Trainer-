#include "max_three.h"

#include <stdio.h>

static int failures = 0;

static void expect_equal(const char *name, int actual, int expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %d, got %d\n", name, expected, actual);
        ++failures;
    }
}

int main(void)
{
    expect_equal("ascending", max_of_three(1, 5, 9), 9);
    expect_equal("middle", max_of_three(-8, 4, 2), 4);
    expect_equal("first", max_of_three(7, 7, -1), 7);
    expect_equal("negative", max_of_three(-9, -3, -12), -3);
    if (failures == 0) {
        puts("PASS max of three");
    }
    return failures == 0 ? 0 : 1;
}
