#include "count_positive.h"

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
    const int mixed[] = {-2, 0, 5, 9, -1, 3};
    const int negative[] = {-3, -2, -1};
    expect_equal("mixed", count_positive(mixed, 6U), 3U);
    expect_equal("negative", count_positive(negative, 3U), 0U);
    expect_equal("empty", count_positive(NULL, 0U), 0U);
    if (failures == 0) {
        puts("PASS count positive");
    }
    return failures == 0 ? 0 : 1;
}
