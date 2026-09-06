#include "sample_mean.h"

double sample_mean(const double *samples, size_t count)
{
    if (!samples || count == 0U) {
        return 0.0;
    }
    double sum = 0.0;
    for (size_t i = 0U; i < count; ++i) {
        sum += samples[i];
    }
    return sum / (double)count;
}
