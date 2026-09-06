#include "debounce.h"

#include <stdio.h>

static int failures = 0;

static void expect_state(debounce_t *button, unsigned int sample, unsigned int expected, const char *name)
{
    unsigned int actual = debounce_update(button, sample);
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %u, got %u\n", name, expected, actual);
        ++failures;
    }
}

int main(void)
{
    debounce_t button;
    debounce_init(&button, 0U, 3U);

    expect_state(&button, 1U, 0U, "press bounce 1");
    expect_state(&button, 0U, 0U, "press bounce reset");
    expect_state(&button, 1U, 0U, "press stable sample 1");
    expect_state(&button, 1U, 0U, "press stable sample 2");
    expect_state(&button, 1U, 1U, "press accepted");

    expect_state(&button, 0U, 1U, "release sample 1");
    expect_state(&button, 1U, 1U, "release bounce reset");
    expect_state(&button, 0U, 1U, "release stable sample 1");
    expect_state(&button, 0U, 1U, "release stable sample 2");
    expect_state(&button, 0U, 0U, "release accepted");

    debounce_init(&button, 9U, 1U);
    expect_state(&button, 2U, 1U, "normalize initial and stable input");
    expect_state(&button, 0U, 0U, "threshold one releases immediately");
    expect_state(&button, 7U, 1U, "threshold one normalizes press");

    debounce_init(&button, 0U, 2U);
    expect_state(&button, 2U, 0U, "normalized candidate first sample");
    expect_state(&button, 5U, 1U, "different nonzero samples are same state");

    if (failures == 0) {
        puts("PASS debounce");
    }
    return failures == 0 ? 0 : 1;
}
