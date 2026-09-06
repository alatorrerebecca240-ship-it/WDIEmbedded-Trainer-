#include "safe_average.h"

double average_ints(const int *values, size_t count)
{
    if (count == 0U) {
        return 0.0;
    }
    /* 用浮点数累加，避免先在 int 中求和而溢出。 */
    double sum = 0.0;
    for (size_t i = 0U; i < count; ++i) {
        sum += (double)values[i];
    }
    return sum / (double)count;
}
