#include "path_parts.h"

size_t count_path_parts(const char *path)
{
    if (!path) {
        return 0U;
    }
    size_t count = 0U;
    int in_component = 0;
    for (; *path != '\0'; ++path) {
        if (*path == '/') {
            in_component = 0;
        } else if (!in_component) {
            ++count;
            in_component = 1;
        }
    }
    return count;
}
