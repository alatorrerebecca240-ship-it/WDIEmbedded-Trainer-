#include "clamp_int.hpp"

#include <iostream>

namespace {
int failures = 0;

void expect_equal(const char *name, int actual, int expected)
{
    if (actual != expected) {
        std::cerr << "FAIL " << name << ": expected " << expected << ", got " << actual << '\n';
        ++failures;
    }
}
}

int main()
{
    expect_equal("inside", clamp_int(5, 0, 10), 5);
    expect_equal("below", clamp_int(-3, 0, 10), 0);
    expect_equal("above", clamp_int(14, 0, 10), 10);
    expect_equal("lower boundary", clamp_int(-5, -5, 8), -5);
    expect_equal("single value", clamp_int(7, 7, 7), 7);
    if (failures == 0) {
        std::cout << "PASS clamp int\n";
    }
    return failures == 0 ? 0 : 1;
}
