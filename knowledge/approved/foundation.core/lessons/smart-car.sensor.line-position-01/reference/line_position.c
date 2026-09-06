#include "line_position.h"

int32_t line_position_three(uint16_t left, uint16_t center, uint16_t right)
{
    int32_t total = (int32_t)left + (int32_t)center + (int32_t)right;
    if (total == 0) {
        return 0;
    }
    /* 先转有符号宽类型，使左偏保持负数，避免无符号减法回绕。 */
    int32_t weighted = ((int32_t)right - (int32_t)left) * 1000;
    return weighted / total;
}
