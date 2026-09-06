#include "apply_operation.h"

int apply_operation(binary_operation op, int a, int b, int *result)
{
    if (!op || !result) {
        return 0;
    }
    *result = op(a, b);
    return 1;
}
