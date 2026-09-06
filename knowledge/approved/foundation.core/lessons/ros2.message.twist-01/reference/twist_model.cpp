#include "twist_model.hpp"

Twist make_planar_twist(double forward, double yaw_rate)
{
    return {{forward, 0.0, 0.0}, {0.0, 0.0, yaw_rate}};
}
