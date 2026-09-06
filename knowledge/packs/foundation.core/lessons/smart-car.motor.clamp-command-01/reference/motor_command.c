#include "motor_command.h"

int16_t clamp_motor_command(int32_t command, int16_t limit)
{
    int32_t bound = limit;
    if (command > bound) {
        return limit;
    }
    if (command < -bound) {
        return (int16_t)(-bound);
    }
    return (int16_t)command;
}
