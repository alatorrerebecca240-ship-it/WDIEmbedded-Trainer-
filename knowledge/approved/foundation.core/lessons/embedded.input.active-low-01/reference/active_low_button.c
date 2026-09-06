#include "active_low_button.h"

bool active_low_pressed(uint8_t pin_level)
{
    return pin_level == 0U;
}
