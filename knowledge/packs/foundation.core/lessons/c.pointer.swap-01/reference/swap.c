#include "swap.h"

void swap_ints(int *left, int *right)
{
    /* 临时变量存放整数本身，不是未初始化的指针。 */
    int temporary = *left;
    *left = *right;
    *right = temporary;
}
