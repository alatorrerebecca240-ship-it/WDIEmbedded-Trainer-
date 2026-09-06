#include "pid.hpp"

#include <cmath>
#include <iostream>

static int failures = 0;

static void expect_near(double actual, double expected, const char *name)
{
    if (std::abs(actual - expected) > 1e-9) {
        std::cerr << "FAIL " << name << ": expected " << expected << ", got " << actual << '\n';
        ++failures;
    }
}

int main()
{
    PidController proportional({2.0, 0.0, 0.0, -10.0, 10.0});
    expect_near(proportional.update(3.0, 0.1), 6.0, "proportional output");

    PidController integral({0.0, 1.0, 0.0, -0.5, 0.5});
    expect_near(integral.update(2.0, 0.1), 0.2, "integral first update");
    expect_near(integral.update(2.0, 1.0), 0.5, "integral upper clamp");

    PidController derivative({0.0, 0.0, 1.0, -10.0, 10.0});
    expect_near(derivative.update(1.0, 0.5), 0.0, "first derivative is zero");
    expect_near(derivative.update(2.0, 0.5), 2.0, "derivative output");
    derivative.reset();
    expect_near(derivative.update(5.0, 0.5), 0.0, "reset clears previous error");
    expect_near(derivative.update(10.0, 0.0), 0.0, "invalid dt returns zero");

    if (failures == 0) {
        std::cout << "PASS pid controller\n";
    }
    return failures == 0 ? 0 : 1;
}

