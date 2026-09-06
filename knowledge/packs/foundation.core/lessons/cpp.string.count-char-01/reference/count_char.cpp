#include "count_char.hpp"

std::size_t count_char(const std::string &text, char target)
{
    std::size_t count = 0U;
    for (char character : text) {
        if (character == target) {
            ++count;
        }
    }
    return count;
}
