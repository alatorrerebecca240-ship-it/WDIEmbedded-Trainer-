# Embedded Trainer

## 0.11.0：新生训练营路线图

在原有插件和题库上增加路线层：7 个能力阶段、49 道必做题、逐层提示、阶段自查和本地报告导出。不按周划分，不迁移题目或覆盖进度；完整题库继续保留。路线模板只引用题目 ID，可通过工作区 `trainer-roadmap.json` 扩展。详见 [训练营说明](docs/training-camp.md)。

WDI 内部代码训练、题库更新与发布项目。公开源码仓库：[WDIEmbedded-Trainer-](https://github.com/alatorrerebecca240-ship-it/WDIEmbedded-Trainer-)。

一个面向 C、C++、嵌入式、智能车、电子设计竞赛、Linux 和 ROS 2 基础的本地训练框架。当前版本以“零第三方 Python 依赖”为目标：训练核心使用 Python 标准库，练习使用 GCC/Clang 编译，VS Code 负责编辑、任务入口和课程树界面。

## 0.9.0：一键获取 + 集中审核

日常只保留两个维护入口：**获取新题**（接管旧草稿、自动筛选/去重、逐题导入并提交云端验证）和 **集中审核**（查看问题、批量人工确认、单独准备发布快照）。失败题独立保留，不阻塞其他题；不自动授予信任或发布。

安装 `apps/vscode-extension/embedded-trainer-0.9.0.vsix` 后重载窗口。首次云端使用须把本轮工具和 `acquire-review.yml` 推送到目标仓库 main，再通过 VS Code 登录 GitHub；未配置时本地草稿仍可保留和浏览。详见 [简化流程指南](docs/authoring-inbox.md)。

## 0.8.0：Exercism 批量导入草稿（保留为高级工具）

插件新增原生维护者菜单：课程视图“…” → “批量获取开源题目”，或“管理知识包” → “维护者：批量获取开源题目”。支持扫描 C/C++ 基础练习、按知识点筛选、多选导入、缓存目录和草稿静态报告，无需输入终端命令。

首批选择 32 个不同母题（24 C、8 C++；25 入门、7 进阶），保留固定提交的完整原题、测试、参考源码、许可证及文件校验。仅提供中文学习目标，完整题干翻译、初始接口和 Docker 编译测试仍待审核；不会自动加入原有 198 题、提交 Git 或发布。详见 [批量获取指南](docs/exercism-import.md)。

安装 `apps/vscode-extension/embedded-trainer-0.8.0.vsix` 后重新加载 VS Code。新导入包使用 0.8.0 引擎的独立依赖许可证校验；已有基础包无需更换。

## 0.7.0：原生风格练习工作台

课程界面采用紧凑的 VS Code 原生风格，加入细线、冷色强调和等宽编号，兼容深浅与高对比度主题。题目和操作位于主区域，状态、知识点、前置课程与知识包信息集中展示；窄分屏自动变为单列。原生课程树显示每组已通过题数，查看提示时保留当前作答草稿。

安装 `apps/vscode-extension/embedded-trainer-0.7.0.vsix` 后重新加载 VS Code，即可使用新版；不需要更换题库，原有练习和进度保持不变。界面说明见插件顶部“使用说明”。本次更新不改变题库审核、代码信任及评测流程。

## 0.6.0：独立知识包

题库已经从插件中分离：当前 198 道题保存在 `knowledge/packs/foundation.core/`，由 `trainer-packs.json` 加载。插件自带训练引擎，不携带题库；支持清单订阅、版本更新、SHA-256 校验、缓存、回退和离线 ZIP 导入。新增代码阅读、纠错题型，保留原四种题型。

维护者可通过 `trainer.py packs` 获取固定提交的开源素材、声明式转换、参数模板和本地 Ollama 生成草稿，再经过人工审核与 GitHub Actions Docker 验证发布。已有 14 道第三方导入草稿和 20 道模板草稿，尚未加入正式课程。

完整操作、格式、许可与安全边界、免费 GitHub 发布配置见 [知识包工作流](docs/knowledge-pack-workflow.md)。项目原创代码与题目采用 [MIT](LICENSE)，第三方代码保留原许可证。首个审核包 **foundation.core 1.0.0（198 题）** 已发布到 [knowledge-v1.0.0 Release](https://github.com/alatorrerebecca240-ship-it/WDIEmbedded-Trainer-/releases/tag/knowledge-v1.0.0)，[发布验证与部署](https://github.com/alatorrerebecca240-ship-it/WDIEmbedded-Trainer-/actions/runs/34013079842)全部通过。后续草稿仍不能跳过审核发布。

学习者安装 VSIX 后在课程树上方点“管理知识包”，无需打开终端；首次使用本项目可直接继续原来的 198 道练习。

### 安装公开题库（无需终端）

1. 在插件中打开“管理知识包” → “添加题库清单来源”。
2. 填入 [Pages 题库清单](https://alatorrerebecca240-ship-it.github.io/WDIEmbedded-Trainer-/catalog.json)的完整地址并确认来源。
3. 返回“管理知识包” → “浏览并安装知识包”，选择“基础课程合集”1.0.0。

其他电脑安装同一插件后可以订阅这个地址，不必克隆题库源码。知识题可直接作答；编程评测还需要本机编译器，并在阅读代码后单独确认“信任知识包代码”。发布审核不等于自动授予本机代码执行权限。

离线使用可从 Release 下载 ZIP 与独立的 .sha256 文件，通过插件“离线导入 ZIP”安装。首发 ZIP 的 SHA-256 是 `5405c047cafdfccf6bf750ce81e931045df25b9eeb825e2e04205e50842cf081`。题库版本与插件版本分别管理；代码和个人学习进度不上传到公开清单。

## 命令行备用入口

Windows PowerShell：

```powershell
.\scripts\bootstrap.ps1
.\trainer.cmd list
.\trainer.cmd start c.pointer.swap-01
.\trainer.cmd check c.pointer.swap-01
```

Linux、macOS 或 Dev Container：

```bash
bash scripts/bootstrap.sh
./trainer.sh list
./trainer.sh start c.pointer.swap-01
./trainer.sh check c.pointer.swap-01
```

开始练习后，代码位于 `exercises/<课程 ID>/`。测试失败是初始状态；修改练习代码，直到 `check` 返回通过。

## 已实现命令

```text
trainer doctor                 检查 Python、编译器和可选工具
trainer validate               校验全部课程描述和文件
trainer smoke                  编译全部课程的初始代码
trainer list [--json]          查看课程
trainer show <id>              阅读题目
trainer start <id>             创建独立练习工作区
trainer check <id>             编译并执行自动测试
trainer submit <id> --answer   提交选择、判断或填空题答案
trainer hint <id> [level]      显示分级提示
trainer progress [--json]      查看本机学习进度
```

## 当前题库

目前共有 **198 题**：27 道编程题、69 道单选题、53 道判断题和 49 道填空题。难度分布为 146 道入门题、52 道进阶题，没有刻意加入高难题。

- C 语言基础：62 题，覆盖语法、类型、运算符、控制流、数组、字符串、指针、结构体、动态内存、预处理器和位操作。
- C++ 基础：18 题，覆盖引用、容器、字符串、类、RAII、重载和基础内存管理。
- 嵌入式基础：18 题，覆盖 GPIO、按键、ADC、定时器、中断、UART、看门狗和定宽整数。
- 智能车竞赛：18 题，覆盖循迹传感器、PWM、电机、编码器、PID 和基础闭环控制。
- 电子设计竞赛：18 题，覆盖基础电路、测量、采样、运放、电阻分压、均值和有效值。
- Linux 基础：32 题，覆盖路径、文件操作、权限、Bash 管道与重定向、环境变量和进程。
- ROS 2 基础：32 题，覆盖节点、话题、服务、动作、参数、工作空间、消息、QoS 和 tf2。

新增两条路线各含 2 道编程题、12 道选择题、9 道判断题、9 道填空题。知识题不执行系统命令，只需插件及 Python；四道编程题为可移植的 C/C++ 教学模型，不调用 Linux 系统接口，不依赖 ROS 2。命令知识以 Linux Bash/GNU 工具和 ROS 2 Jazzy 为参考，不是 PowerShell 命令；真正运行 ROS 2 命令需另行配置相应环境。学习顺序与官方参考见两条路线的 README。

## VS Code

安装 `apps/vscode-extension/embedded-trainer-0.6.0.vsix` 后，可以完全通过界面训练：

- 活动栏课程路线按编程题、选择题、判断题和填空题分类。
- 客观题直接在课程面板选择或填写并提交。
- 编程题在课程面板打开代码、运行评测和查看提示。
- Test Explorer 运行一门或全部编程题。
- 编译问题显示在 Problems 面板。
- 状态栏查看完成进度。
- 管理知识包、检查更新、离线导入、回退与版本代码信任均有界面入口。

插件在后台直接调用训练核心，不创建 PowerShell 终端。根目录 `.vscode/tasks.json` 仅作为没有安装插件时的备用入口。插件开发和打包方法见 `apps/vscode-extension/README.md`。

## 可移植性

- 普通模式：安装 Python 3.9+ 和 GCC/Clang，然后运行启动脚本。
- 容器模式：使用 `.devcontainer` 获得一致的 Linux 编译环境。
- 硬件模式：后续通过适配器连接 PlatformIO、厂商工具链、烧录器和串口。

课程格式、扩展方法和架构说明位于 `docs/`。项目原创部分已选择 MIT；发布第三方题目和厂商代码前仍须逐项核对授权，不能覆盖其原始许可证。
