#include "add_service.hpp"
#include <iostream>

int main()
{
    const struct { std::int64_t a, b, expected; } cases[] = {
        {0, 0, 0}, {7, -3, 4}, {-8, -5, -13}, {12, 30, 42}, {9, -9, 0},
        {1000000000000LL, 1000000000000LL, 2000000000000LL},
        {-1000000000000LL, -1000000000000LL, -2000000000000LL},
        {0, -42, -42}, {-1000000000000LL, 1000000000000LL, 0}
    };
    int failures = 0;
    for (const auto &item : cases) {
        AddRequest request{item.a, item.b};
        const auto response = handle_add(request);
        if (response.sum != item.expected || request.a != item.a || request.b != item.b) {
            std::cout << "FAIL a=" << item.a << " b=" << item.b << ": expected "
                      << item.expected << ", got " << response.sum << " (request must remain unchanged)\n";
            ++failures;
        }
    }
    if (!failures) std::cout << "PASS add service model\n";
    return failures ? 1 : 0;
}
