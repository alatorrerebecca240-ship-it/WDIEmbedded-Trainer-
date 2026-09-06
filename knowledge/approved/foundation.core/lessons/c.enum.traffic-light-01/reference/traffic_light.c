#include "traffic_light.h"

TrafficLight next_traffic_light(TrafficLight current)
{
    switch (current) {
    case TRAFFIC_RED:
        return TRAFFIC_GREEN;
    case TRAFFIC_GREEN:
        return TRAFFIC_YELLOW;
    case TRAFFIC_YELLOW:
    default:
        return TRAFFIC_RED;
    }
}
