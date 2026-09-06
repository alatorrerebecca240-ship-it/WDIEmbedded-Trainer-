#include "string_length.h"

size_t string_length(const char *text)
{
    if (!text) {
        return 0U;
    }
    size_t length = 0U;
    while (text[length] != '\0') {
        ++length;
    }
    return length;
}
