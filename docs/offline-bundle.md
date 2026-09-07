# Windows 离线发行包

0.12.0 在原插件“检查训练环境”中加入缺失环境安装。学习者在 VS Code 内选择已经解压的整体包、确认默认位置；后台校验文件、调用随 VSIX 提供的安装脚本、复检并刷新课程。不要求学习者运行终端命令。

## 固定组件

环境版本与 SHA-256 固定在 `apps/vscode-extension/resources/offline-runtime.json`，该文件随 VSIX 打包。外部离线包不能通过修改自己的清单更换要执行的程序。

- Python 3.13.15 Windows x86-64 完整安装器，按当前用户安装。
- LLVM-MinGW 20260826 UCRT x86_64，提供电脑端 C11/C++17 编译器。
- Boost 1.85.0，分发原始 ZIP，安装时只提取头文件及根许可证。

默认位置见插件使用说明。环境路径仅保存在扩展本机状态中，不写系统 PATH，不同步到别的电脑。保留检测可用的 Python 和各语言编译器，不卸载或覆盖它们；拒绝覆盖未知的已有默认目录。

## 维护者构建

1. 从固定官方地址获取三个环境归档，存放在 `.trainer/offline-assets`。保存对应 Python 版本的 `LICENSE` 为 `Python-LICENSE.txt`；另外按 `scripts/offline-source-pins.json` 取得附带工具的 4 份源码归档与构建材料。勿使用来源不明的镜像或同名安装器。
2. 将已经发布的 `knowledge-v1.1.0` 的 50 个拓展 ZIP 和 `catalog.json` 放在 `.trainer/release-downloads/knowledge-v1.1.0`，基础 ZIP 放在 `.trainer/offline-assets`。不重新运行第三方参考代码；构建工具核对发布目录的 51 个 ZIP 哈希和数量。
3. 在 `apps/vscode-extension` 中运行插件测试并构建 VSIX。更新 Word 图文说明后必须渲染并逐页检查。
4. 在仓库根目录运行 `powershell -NoProfile -File scripts/test-offline-archives.ps1`。该测试提取安装器中的实际安全解压函数，只在新建的 `.trainer/environment-test-…` 内解压、编译并执行自行编写的 C/C++ 环境自检程序；不安装 Python、不执行题库代码、不修改全局 PATH。
5. 运行 `python scripts/build-offline-bundle.py`。构建器先验证固定哈希、Python 官方签名、VSIX 版本与脚本、已发布题库哈希和版权文件，再生成 `dist/Embedded-Trainer-0.12.0-Windows-x64-offline.zip` 和对应校验文件。若同名输出已存在，构建会停止，需先保留或重命名旧输出。

目录只通过明确清单复制文件，不打包工作区整体。总包包含 VSIX、3 个环境归档、51 个原始知识包、Word 说明、许可证、附带工具的源码与构建材料、文件清单与 SHA-256；不包含个人源码、学习进度、令牌、执行信任或开发缓存。

## 验证边界

单元测试覆盖环境复用、损坏包阻止执行、取消安装、复检、路径记忆与失败后保持已有环境。真实归档测试覆盖安全解压以及 C11/C++17/Boost 编译和运行。它们不等于在全新 Windows 上验证过 Python 安装器、不同杀毒软件、企业权限策略和首次 VS Code 安装；大规模发放前应在一台干净的 Windows 10/11 x64 电脑试装。

软件安装授权不替代题库代码信任。第三方草稿的参考答案验证仍走 GitHub Actions Docker，不因提供本地编译器而改成原生批量执行。有关版权来源见 `offline-bundle-notices.md`。
