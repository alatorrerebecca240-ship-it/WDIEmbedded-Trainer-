#include "adc_millivolts.h"

uint32_t adc_to_millivolts(uint16_t sample, uint16_t max_code, uint32_t reference_mv)
{
    if (max_code == 0U) {
        return 0U;
    }
    /* 题目约定 reference_mv <= 5000；先扩展再乘，最后四舍五入。 */
    uint32_t scaled = (uint32_t)sample * reference_mv;
    return (scaled + max_code / 2U) / max_code;
}
