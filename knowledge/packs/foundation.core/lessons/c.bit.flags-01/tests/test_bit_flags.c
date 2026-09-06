#include "bit_flags.h"

#include <stdio.h>

static int failures = 0;

static void expect_u8(const char *name, uint8_t actual, uint8_t expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %u, got %u\n", name, (unsigned int)expected, (unsigned int)actual);
        ++failures;
    }
}

static void expect_bool(const char *name, bool actual, bool expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %d, got %d\n", name, (int)expected, (int)actual);
        ++failures;
    }
}

int main(void)
{
    expect_u8("set low", set_bit_u8(0x00U, 0U), 0x01U);
    expect_u8("set high", set_bit_u8(0x01U, 7U), 0x81U);
    expect_u8("clear", clear_bit_u8(0xFFU, 3U), 0xF7U);
    expect_bool("read set", is_bit_set_u8(0x20U, 5U), true);
    expect_bool("read clear", is_bit_set_u8(0x20U, 4U), false);
    if (failures == 0) {
        puts("PASS bit flags");
    }
    return failures == 0 ? 0 : 1;
}
