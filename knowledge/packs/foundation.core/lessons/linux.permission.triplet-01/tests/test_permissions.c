#include "permissions.h"
#include <limits.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    const char *expected[] = {"---", "--x", "-w-", "-wx", "r--", "r-x", "rw-", "rwx"};
    int failures = 0;
    for (unsigned digit = 0; digit < 8; ++digit) {
        char buffer[6] = {'L', '?', '?', '?', '?', 'R'};
        int result = permission_triplet(digit, buffer + 1);
        if (result != 0 || memcmp(buffer + 1, expected[digit], 4) != 0 || buffer[0] != 'L' || buffer[5] != 'R') {
            printf("FAIL permission digit %u (characters, terminator or buffer bounds)\n", digit);
            ++failures;
        }
    }
    const unsigned invalid[] = {8u, 9u, 255u, UINT_MAX};
    for (unsigned i = 0; i < sizeof invalid / sizeof invalid[0]; ++i) {
        char buffer[6] = {'L', 'k', 'e', 'e', 'p', 'R'};
        if (permission_triplet(invalid[i], buffer + 1) != -1 || memcmp(buffer, "LkeepR", 6) != 0) {
            printf("FAIL invalid digit %u must leave output unchanged\n", invalid[i]);
            ++failures;
        }
    }
    if (!failures) puts("PASS permission triplets");
    return failures ? 1 : 0;
}
