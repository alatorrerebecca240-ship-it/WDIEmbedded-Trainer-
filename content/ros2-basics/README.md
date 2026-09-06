# ROS 2 基础

32 题：2 道 C++ 编程题、12 道选择题、9 道判断题、9 道填空题。其中 26 道入门、6 道进阶。

## 学习顺序

1. 节点与程序：节点的职责、节点与进程的区别、ros2 run、node list。
2. 话题与消息：发布/订阅、topic list/echo、消息类型、Twist、interface show。
3. 服务与动作：请求/响应、服务列表、长任务反馈与取消请求。
4. 参数与启动：节点配置、launch 组织多个节点。
5. 包与工作空间：package.xml、colcon build、source 安装环境、rclcpp。
6. 基础进阶：QoS 兼容、ROS_DOMAIN_ID、tf2、执行器回调、bag 记录。
7. 配套编程：构造平面速度结构体、由请求生成响应。

在 VS Code 的 Embedded Trainer 课程树中展开“ROS 2 基础”，按题型选择题目。每题有提示和答对后的解析，未答对可直接重试。

## 版本与环境边界

- 以 ROS 2 Jazzy 的官方入门概念和常用 CLI 为参考，不将 Jazzy 表述为最新版本，也不要求为了做题安装该版本。
- 所有知识题都由训练核心判分，不执行 ros2、colcon 或 source；当前 Windows 电脑仅需原有插件和 Python 即可作答。
- 涉及 setup.bash 的题目明确使用 Linux Bash。实际执行命令之前，需安装匹配发行版及示例包、满足依赖，并在该终端加载环境。
- ros2 命令能观察到什么取决于正在运行的节点和通信配置；域号一致、名称相同都不单独保证通信成功。
- 不讨论复杂 SLAM、导航算法、DDS 内部实现或实时性保证；先建立能阅读和理解入门示例的基础。

## 编程题不是实际 ROS 2 集成测试

twist-model 和 add-service-model 使用普通 C++ 结构体与函数，现有 G++/Clang 即可评测。它们只是学习消息字段和请求响应处理逻辑，没有生成 .msg/.srv 接口、启动 ROS 2 节点或收发真实数据。真实机器人项目还需要相应客户端库、构建配置、执行器和硬件安全措施。

## 题库保存与扩展

客观题位于 question-bank.json；编程题各有 lesson.json、README.md、starter/ 和 tests/。新知识仍可按相同格式追加，使用唯一 ID 与清晰的版本假设，不需要数据库。不要在题目判定器中直接执行学生填写的 shell 命令。

## 官方参考

题干、干扰选项、提示与解析为本项目编写；以下是核对知识和后续实践的资料入口。

- [Jazzy：命令行入门教程](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools.html)
- [官方教程源码：节点](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Nodes/Understanding-ROS2-Nodes.rst)
- [官方教程源码：话题](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.rst)
- [官方教程源码：服务](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Services/Understanding-ROS2-Services.rst)
- [官方教程源码：参数](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Parameters/Understanding-ROS2-Parameters.rst)
- [官方教程源码：工作空间](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.rst)
- [官方文档源码：QoS 兼容性](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Quality-of-Service-Settings.rst)
- [官方文档源码：域 ID](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Domain-ID.rst)
- [官方文档源码：tf2](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Tf2.rst)
- [官方文档源码：执行器](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Executors.rst)
- [geometry_msgs：Twist 定义](https://github.com/ros2/common_interfaces/blob/jazzy/geometry_msgs/msg/Twist.msg)
