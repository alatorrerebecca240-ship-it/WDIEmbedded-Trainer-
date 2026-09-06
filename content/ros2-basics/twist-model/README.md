# 构造平面速度消息

这是借鉴 geometry_msgs/msg/Twist 字段形状的普通 C++ 教学模型，不是 ROS 2 自动生成的消息类型，也不会发布话题或控制真实小车。无需安装 ROS 2。

## 要求

实现 `Twist make_planar_twist(double forward, double yaw_rate)`。

- 采用本题约定的机体坐标：x 向前、y 向左、z 向上。
- forward 是沿 x 的线速度，单位 m/s；写入 linear.x。
- yaw_rate 是绕 z 的角速度，单位 rad/s；写入 angular.z。
- linear.y、linear.z、angular.x、angular.y 都必须为 0。
- 输入保证是有限值且范围为 [-10, 10]；保留正负号，不截断、不取绝对值。
- 返回一个完整初始化的 Twist；不添加 main、不修改头文件。

例如输入 (0.5, -0.2)，linear 应为 (0.5, 0, 0)，angular 应为 (0, 0, -0.2)。

测试覆盖直行、转弯、停止、倒车与小数。真实机器人还需要消息类型生成、节点、发布者、坐标约定与安全限速等，这些不属于本题实现范围。
