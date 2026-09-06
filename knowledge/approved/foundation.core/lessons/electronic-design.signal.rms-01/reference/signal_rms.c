#include "signal_rms.h"

#include <math.h>

double signal_rms(const float *samples, size_t count)
{
    if (!samples || count == 0U) {
        return 0.0;
    }
    double square_sum = 0.0;
    for (size_t i = 0U; i < count; ++i) {
        double value = (double)samples[i];
        square_sum += value * value;
    }
    return sqrt(square_sum / (double)count);
}
