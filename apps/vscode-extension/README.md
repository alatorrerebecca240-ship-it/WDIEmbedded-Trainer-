# Embedded Trainer VS Code Extension

Embedded Trainer 0.9.0 用独立知识包驱动 C/C++、嵌入式、智能车、电赛、Linux 和 ROS 2 训练，不要求学习者手动使用 PowerShell。支持编程、选择、判断、填空、代码阅读和纠错六种题型。

维护流程已简化为 **获取新题** 与 **集中审核** 两个入口，位于课程视图“…”及“管理知识包”。自动接管旧草稿、筛选去重、逐题导入，并通过 GitHub Actions 验证；失败题不阻塞其他题。首次需要部署仓库工作流和 VS Code GitHub 登录，缺少配置时保留本地草稿。审核和准备发布仍需明确确认，绝不自动推送或发布。

新增维护者入口：课程视图“…” → “批量获取开源题目”。通过原生选择列表扫描 Exercism C/C++、筛选知识点、批量导入草稿及生成静态报告。只下载和转换数据，不执行、启用或自动审核题目；参考代码仅在人工启动的 GitHub Actions Docker 流程中验证。完整操作说明已加入插件帮助。

## 界面功能

- 活动栏“Embedded Trainer”课程路线，按 C、C++、嵌入式、智能车、电赛、Linux 和 ROS 2 分组。
- 紧凑的原生风格课程工作台：细线、冷色强调、等宽编号，跟随深浅及高对比度主题，窄分屏自动调整布局。
- 课程面板提供开始练习、打开代码、运行评测、分级提示和完整题目按钮；查看提示时保留当前作答草稿，防止重复提交。
- VS Code Test Explorer 原生测试项及运行结果。
- 编译错误进入 Problems 面板并可跳转到源码。
- 状态栏显示已完成课程数量。
- 评测过程在后台直接启动 Python，不创建终端。
- 插件内置中文使用说明，可从课程视图顶部的问号按钮打开。
- 课程视图顶部包图标：添加可信 GitHub Pages 清单、安装和更新知识包、离线 ZIP 导入、版本回退及代码信任。
- 使用 VS Code Settings Sync 同步题库订阅，各电脑独立下载；不把学习进度或私人代码上传到公开仓库。

## 使用开发版本

用 VS Code 打开项目根目录，然后选择“运行和调试”中的 `Run and Debug: Embedded Trainer Extension`。

## 安装 VSIX

选择 `embedded-trainer-0.9.0.vsix`，在 VS Code 扩展视图菜单中“从 VSIX 安装”，然后重新加载窗口。VSIX 包含界面、帮助及 Python 训练引擎，不包含题库或私人答案。新电脑需要 Python 3.9+，编程评测另需 GCC/G++；无需复制或克隆项目，添加已经发布的题库清单或离线导入审核包即可。

本项目工作区通过 `trainer-packs.json` 加载分离后的 198 道本地基础题。已发布的 `foundation.core 1.0.0` 可从[公共清单](https://alatorrerebecca240-ship-it.github.io/WDIEmbedded-Trainer-/catalog.json)安装；新版本知识包仍需审核后发布。原创部分采用 MIT，学习者说明见插件内问号，维护者工作流见根目录 `docs/knowledge-pack-workflow.md`。

打包命令：

```text
npm run package
```

当前按 MIT 提供源码和本地 VSIX。若发布到 VS Code Marketplace，仍需注册自己的发布者；GitHub 知识包发布不依赖 Marketplace。
