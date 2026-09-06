#ifndef TRAINER_TWIST_MODEL_HPP
#define TRAINER_TWIST_MODEL_HPP
struct Vector3 { double x; double y; double z; };
struct Twist { Vector3 linear; Vector3 angular; };
Twist make_planar_twist(double forward, double yaw_rate);
#endif
