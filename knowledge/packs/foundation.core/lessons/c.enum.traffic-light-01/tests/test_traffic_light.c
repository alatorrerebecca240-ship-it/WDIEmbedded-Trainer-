#include "traffic_light.h"

#include <stdio.h>

static int failures = 0;

static void expect_state(const char *name, TrafficLight actual, TrafficLight expected)
{
    if (actual != expected) {
        fprintf(stderr, "FAIL %s: expected %d, got %d\n", name, (int)expected, (int)actual);
        ++failures;
    }
}

int main(void)
{
    expect_state("red", next_traffic_light(TRAFFIC_RED), TRAFFIC_GREEN);
    expect_state("green", next_traffic_light(TRAFFIC_GREEN), TRAFFIC_YELLOW);
    expect_state("yellow", next_traffic_light(TRAFFIC_YELLOW), TRAFFIC_RED);
    expect_state("invalid", next_traffic_light((TrafficLight)99), TRAFFIC_RED);
    if (failures == 0) {
        puts("PASS traffic light");
    }
    return failures == 0 ? 0 : 1;
}
