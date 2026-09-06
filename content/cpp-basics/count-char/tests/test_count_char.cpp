#include "count_char.hpp"

#include <iostream>

namespace {
int failures = 0;

void expect_equal(const char *name, std::size_t actual, std::size_t expected)
{
    if (actual != expected) {
        std::cerr << "FAIL " << name << ": expected " << expected << ", got " << actual << '\n';
        ++failures;
    }
}
}

int main()
{
    expect_equal("repeated", count_char("embedded", 'e'), 3U);
    expect_equal("missing", count_char("vehicle", 'x'), 0U);
    expect_equal("case sensitive", count_char("AaA", 'A'), 2U);
    expect_equal("empty", count_char("", 'a'), 0U);
    if (failures == 0) {
        std::cout << "PASS count char\n";
    }
    return failures == 0 ? 0 : 1;
}
