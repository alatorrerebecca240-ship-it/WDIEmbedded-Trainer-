#include "adc_millivolts.h"

#include <inttypes.h>
#include <stdio.h>

static int failures = 0;

static void expect_equal(const char *name, uint32_t actual, uint32_t expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %" PRIu32 ", got %" PRIu32 "\n", name, expected, actual);
        ++failures;
    }
}

int main(void)
{
    expect_equal("zero", adc_to_millivolts(0U, 4095U, 3300U), 0U);
    expect_equal("full scale", adc_to_millivolts(4095U, 4095U, 3300U), 3300U);
    expect_equal("half scale", adc_to_millivolts(2048U, 4095U, 3300U), 1650U);
    expect_equal("quarter scale", adc_to_millivolts(1024U, 4095U, 3300U), 825U);
    expect_equal("invalid max", adc_to_millivolts(10U, 0U, 3300U), 0U);
    expect_equal("round half up", adc_to_millivolts(1U, 2U, 1U), 1U);
    expect_equal("largest codes", adc_to_millivolts(UINT16_MAX, UINT16_MAX, 5000U), 5000U);
    if (failures == 0) {
        puts("PASS ADC millivolts");
    }
    return failures == 0 ? 0 : 1;
}
