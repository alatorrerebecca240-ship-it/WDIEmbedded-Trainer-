#include "string_length.h"

#include <stdio.h>

static int failures = 0;

static void expect_equal(const char *name, size_t actual, size_t expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %zu, got %zu\n", name, expected, actual);
        ++failures;
    }
}

int main(void)
{
    expect_equal("empty", string_length(""), 0U);
    expect_equal("embedded", string_length("car"), 3U);
    expect_equal("spaces", string_length("a b c"), 5U);
    expect_equal("null", string_length(NULL), 0U);
    if (failures == 0) {
        puts("PASS string length");
    }
    return failures == 0 ? 0 : 1;
}
