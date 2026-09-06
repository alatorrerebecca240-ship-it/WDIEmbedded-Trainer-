#include "reverse_array.h"

#include <stdio.h>

static int failures = 0;

static void expect_array(const char *name, const int *actual, const int *expected, size_t count)
{
    size_t index;
    for (index = 0U; index < count; ++index) {
        if (actual[index] != expected[index]) {
            fprintf(stderr, "FAIL %s[%zu]: expected %d, got %d\n", name, index, expected[index], actual[index]);
            ++failures;
            return;
        }
    }
}

int main(void)
{
    int even[] = {1, 2, 3, 4};
    const int even_expected[] = {4, 3, 2, 1};
    int odd[] = {-1, 0, 8};
    const int odd_expected[] = {8, 0, -1};
    reverse_ints(even, 4U);
    reverse_ints(odd, 3U);
    reverse_ints(NULL, 0U);
    expect_array("even", even, even_expected, 4U);
    expect_array("odd", odd, odd_expected, 3U);
    if (failures == 0) {
        puts("PASS reverse array");
    }
    return failures == 0 ? 0 : 1;
}
