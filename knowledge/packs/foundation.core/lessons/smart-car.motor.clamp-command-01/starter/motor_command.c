#include "motor_command.h"

int16_t clamp_motor_command(int32_t command, int16_t limit)
{
    /* TODO: 将 command 限制在 [-limit, limit]。 */
    (void)limit;
    return (int16_t)command;
}
