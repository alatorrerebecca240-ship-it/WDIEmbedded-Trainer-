#include "reverse_array.h"

void reverse_ints(int *values, size_t count)
{
    for (size_t i = 0U; i < count / 2U; ++i) {
        size_t opposite = count - 1U - i;
        int temporary = values[i];
        values[i] = values[opposite];
        values[opposite] = temporary;
    }
}
