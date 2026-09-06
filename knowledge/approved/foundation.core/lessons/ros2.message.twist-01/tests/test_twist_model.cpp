#include "twist_model.hpp"
#include <cmath>
#include <iostream>

int main()
{
    const double cases[][2] = {{0, 0}, {1, 0}, {0, 1}, {0.5, -0.2}, {-2, 0.75}, {-10, 10}, {0.001, -0.001}};
    int failures = 0;
    for (const auto &input : cases) {
        const auto value = make_planar_twist(input[0], input[1]);
        const double actual[] = {value.linear.x, value.linear.y, value.linear.z, value.angular.x, value.angular.y, value.angular.z};
        const double expected[] = {input[0], 0, 0, 0, 0, input[1]};
        for (int i = 0; i < 6; ++i) {
            if (!(std::fabs(actual[i] - expected[i]) <= 1e-12)) {
                std::cout << "FAIL forward=" << input[0] << " yaw=" << input[1] << " component " << i
                          << ": expected " << expected[i] << ", got " << actual[i] << '\n';
                ++failures;
            }
        }
    }
    if (!failures) std::cout << "PASS planar twist\n";
    return failures ? 1 : 0;
}
