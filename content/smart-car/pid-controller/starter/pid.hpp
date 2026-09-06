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
        /* TODO: 实现比例、积分、微分和积分限幅。 */
        (void)error;
        (void)dt;
        return 0.0;
    }

    void reset()
    {
        /* TODO: 清除控制器状态。 */
    }

private:
    PidConfig config_;
    double integral_{0.0};
    double previous_error_{0.0};
    bool has_previous_{false};
};

#endif

