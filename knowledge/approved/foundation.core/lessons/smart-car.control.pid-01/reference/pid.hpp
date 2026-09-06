#ifndef TRAINER_PID_HPP
#define TRAINER_PID_HPP

struct PidConfig {
    double kp;
    double ki;
    double kd;
    double integral_min;
    double integral_max;
};

class PidController {
public:
    explicit PidController(PidConfig config) : config_(config) {}

    double update(double error, double dt)
    {
        if (dt <= 0.0) {
            return 0.0;
        }
        integral_ += error * dt;
        if (integral_ < config_.integral_min) {
            integral_ = config_.integral_min;
        }
        if (integral_ > config_.integral_max) {
            integral_ = config_.integral_max;
        }
        double derivative = has_previous_ ? (error - previous_error_) / dt : 0.0;
        previous_error_ = error;
        has_previous_ = true;
        return config_.kp * error + config_.ki * integral_ + config_.kd * derivative;
    }

    void reset()
    {
        integral_ = 0.0;
        previous_error_ = 0.0;
        has_previous_ = false;
    }

private:
    PidConfig config_;
    double integral_{0.0};
    double previous_error_{0.0};
    bool has_previous_{false};
};

#endif
