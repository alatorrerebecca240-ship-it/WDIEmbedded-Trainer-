# 带积分限幅的 PID 控制器

补全 `pid.hpp` 中的 `PidController`，用于智能车电机速度或转向控制。

## 数学形式

```text
integral += error * dt
derivative = (error - previous_error) / dt
output = kp * error + ki * integral + kd * derivative
```

## 要求

- `dt` 必须大于 0，否则返回 0 且不改变内部状态。
- 积分状态限制在 `[integral_min, integral_max]`。
- 第一次有效更新的微分项为 0。
- `reset()` 恢复初始状态。

