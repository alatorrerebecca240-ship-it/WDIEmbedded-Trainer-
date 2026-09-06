#include "apply_operation.h"

#include <stdio.h>

static int failures = 0;
static int callback_calls = 0;

static int add(int left, int right)
{
    ++callback_calls;
    return left + right;
}

static int multiply(int left, int right)
{
    return left * right;
}

static void expect_equal(const char *name, int actual, int expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %d, got %d\n", name, expected, actual);
        ++failures;
    }
}

int main(void)
{
    int result = 123;
    expect_equal("add status", apply_operation(add, 7, -2, &result), 1);
    expect_equal("add result", result, 5);
    expect_equal("multiply status", apply_operation(multiply, 6, 4, &result), 1);
    expect_equal("multiply result", result, 24);
    result = 123;
    expect_equal("null callback", apply_operation(NULL, 1, 2, &result), 0);
    expect_equal("result unchanged", result, 123);
    expect_equal("null result", apply_operation(add, 1, 2, NULL), 0);
    expect_equal("callback skipped for invalid pointers", callback_calls, 1);
    if (failures == 0) {
        puts("PASS apply operation");
    }
    return failures == 0 ? 0 : 1;
}
