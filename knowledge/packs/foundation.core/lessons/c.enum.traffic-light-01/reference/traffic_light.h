#ifndef TRAINER_TRAFFIC_LIGHT_H
#define TRAINER_TRAFFIC_LIGHT_H

typedef enum {
    TRAFFIC_RED,
    TRAFFIC_YELLOW,
    TRAFFIC_GREEN
} TrafficLight;

TrafficLight next_traffic_light(TrafficLight current);

#endif
