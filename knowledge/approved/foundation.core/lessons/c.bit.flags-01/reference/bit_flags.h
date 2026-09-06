#ifndef TRAINER_BIT_FLAGS_H
#define TRAINER_BIT_FLAGS_H

#include <stdbool.h>
#include <stdint.h>

uint8_t set_bit_u8(uint8_t value, unsigned int bit);
uint8_t clear_bit_u8(uint8_t value, unsigned int bit);
bool is_bit_set_u8(uint8_t value, unsigned int bit);

#endif
