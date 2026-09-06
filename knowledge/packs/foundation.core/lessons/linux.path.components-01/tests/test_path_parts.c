#include "path_parts.h"
#include <stdio.h>

int main(void)
{
    const struct { const char *path; size_t expected; } cases[] = {
        {NULL, 0}, {"", 0}, {"/", 0}, {"////", 0}, {"a", 1}, {"a/", 1},
        {"/a", 1}, {"logs//today/", 2}, {"/home/student/src", 3},
        {"./src/../include", 4}, {"my notes/file.txt", 2},
        {"///a///b//c///", 3}, {".", 1}, {"..", 1}, {" / ", 2}
    };
    int failures = 0;
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; ++i) {
        size_t actual = count_path_parts(cases[i].path);
        if (actual != cases[i].expected) {
            /* Keep diagnostics compatible with older Windows C runtimes. */
            printf("FAIL path case %lu: expected %lu, got %lu\n",
                   (unsigned long)i, (unsigned long)cases[i].expected, (unsigned long)actual);
            ++failures;
        }
    }
    if (!failures) puts("PASS path components");
    return failures ? 1 : 0;
}
