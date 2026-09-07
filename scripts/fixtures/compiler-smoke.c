#include <stdio.h>

int main(void) {
    int left = 2;
    int right = 3;
    int temporary = left;
    left = right;
    right = temporary;
    puts("C11 environment smoke test");
    return left == 3 && right == 2 ? 0 : 1;
}
