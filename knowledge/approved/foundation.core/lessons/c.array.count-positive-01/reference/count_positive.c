#include "count_positive.h"

size_t count_positive(const int *values, size_t count)
{
    size_t positives = 0U;
    for (size_t i = 0U; i < count; ++i) {
        if (values[i] > 0) {
            ++positives;
        }
    }
    return positives;
}
