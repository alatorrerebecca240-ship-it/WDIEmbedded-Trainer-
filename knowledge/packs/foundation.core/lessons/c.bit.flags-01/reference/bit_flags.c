#include "bit_flags.h"

uint8_t set_bit_u8(uint8_t value, unsigned int bit)
{
    return (uint8_t)(value | (1U << bit));
}

uint8_t clear_bit_u8(uint8_t value, unsigned int bit)
{
    return (uint8_t)(value & ~(1U << bit));
}

bool is_bit_set_u8(uint8_t value, unsigned int bit)
{
    return (value & (1U << bit)) != 0U;
}
