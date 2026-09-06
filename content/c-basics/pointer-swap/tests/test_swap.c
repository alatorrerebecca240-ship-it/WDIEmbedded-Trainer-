#include "swap.h"

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
    int left = 7;
    int right = -3;
    swap_ints(&left, &right);
    expect_equal("left after swap", left, -3);
    expect_equal("right after swap", right, 7);

    int same = 42;
    swap_ints(&same, &same);
    expect_equal("same address", same, 42);

    if (failures == 0) {
        puts("PASS pointer swap");
    }
    return failures == 0 ? 0 : 1;
}

