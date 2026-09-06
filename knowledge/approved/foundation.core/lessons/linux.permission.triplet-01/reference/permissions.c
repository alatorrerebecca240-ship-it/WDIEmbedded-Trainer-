#include "permissions.h"

int permission_triplet(unsigned digit, char output[4])
{
    if (digit > 7U) {
        return -1;
    }
    output[0] = (digit & 4U) ? 'r' : '-';
    output[1] = (digit & 2U) ? 'w' : '-';
    output[2] = (digit & 1U) ? 'x' : '-';
    output[3] = '\0';
    return 0;
}
