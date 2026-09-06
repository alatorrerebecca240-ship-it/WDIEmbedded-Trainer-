#ifndef TRAINER_MOTOR_COMMAND_H
#define TRAINER_MOTOR_COMMAND_H

#include <stdint.h>

int16_t clamp_motor_command(int32_t command, int16_t limit);

#endif
