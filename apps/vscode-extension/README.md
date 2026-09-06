# Embedded Trainer VS Code Extension

Embedded Trainer 0.6.0 用独立知识包驱动 C/C++、嵌入式、智能车、电赛、Linux 和 ROS 2 训练，不要求学习者手动使用 PowerShell。支持编程、选择、判断、填空、代码阅读和纠错六种题型。

## 界面功能

- 活动栏“Embedded Trainer”课程路线，按 C、C++、嵌入式、智能车、电赛、Linux 和 ROS 2 分组。
- 课程详情面板，提供开始练习、打开代码、运行评测、分级提示和完整题目按钮。
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

选择 `embedded-trainer-0.6.0.vsix`，在 VS Code 扩展视图菜单中“从 VSIX 安装”，然后重新加载窗口。VSIX 包含界面、帮助及 Python 训练引擎，不包含题库或私人答案。新电脑需要 Python 3.9+，编程评测另需 GCC/G++；无需复制或克隆项目，添加已经发布的题库清单或离线导入审核包即可。

本项目工作区通过 `trainer-packs.json` 加载分离后的 198 道本地基础题。仓库已指定为 `alatorrerebecca240-ship-it/WDIEmbedded-Trainer-`，原创部分采用 MIT；知识包仍需审核后发布，源码上传不代表题库清单已经上线。学习者说明见插件内问号，维护者工作流见根目录 `docs/knowledge-pack-workflow.md`。

打包命令：

```text
npm run package
```

当前按 MIT 提供源码和本地 VSIX。若发布到 VS Code Marketplace，仍需注册自己的发布者；GitHub 知识包发布不依赖 Marketplace。
