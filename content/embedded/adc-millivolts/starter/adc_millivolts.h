#ifndef TRAINER_ADC_MILLIVOLTS_H
#define TRAINER_ADC_MILLIVOLTS_H

#include <stdint.h>

uint32_t adc_to_millivolts(uint16_t sample, uint16_t max_code, uint32_t reference_mv);

#endif
