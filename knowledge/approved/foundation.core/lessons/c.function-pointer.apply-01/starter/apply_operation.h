#ifndef TRAINER_APPLY_OPERATION_H
#define TRAINER_APPLY_OPERATION_H

typedef int (*binary_operation)(int left, int right);

int apply_operation(binary_operation op, int a, int b, int *result);

#endif
