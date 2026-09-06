#include "list_count.h"

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
    Node third = {30, NULL};
    Node second = {20, &third};
    Node first = {10, &second};
    Node single = {99, NULL};
    expect_equal("empty", list_count(NULL), 0U);
    expect_equal("single", list_count(&single), 1U);
    expect_equal("three", list_count(&first), 3U);
    if (failures == 0) {
        puts("PASS list count");
    }
    return failures == 0 ? 0 : 1;
}
