# 限制电机控制指令

实现 `clamp_motor_command(command, limit)`，把 32 位控制计算结果限制到 `[-limit, limit]`，再以 `int16_t` 返回。

测试保证 `limit` 位于 0 到 32767。正值和负值可以分别表示两个驱动方向。
