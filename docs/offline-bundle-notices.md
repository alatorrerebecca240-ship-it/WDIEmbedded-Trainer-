# 离线发行包来源与许可证

本离线包是多项目软件的集合，不代表所有内容统一改为 MIT，也不代表上游项目认可或担保本插件。

## 插件与基础题库

Embedded Trainer 原创源码采用 MIT。副本见 `Embedded-Trainer-MIT.txt`；基础知识包内也保留了许可证。仓库为 https://github.com/alatorrerebecca240-ship-it/WDIEmbedded-Trainer- 。

51 个知识包使用已发布的 `knowledge-v1.1.0` 原始 ZIP，不修改题目或重新运行第三方参考代码。包内的来源、许可证和署名应与 ZIP 一起保留。50 个 Exercism 拓展包包含其自身以及测试框架等依赖的版权记录，具体以各包 `licenses` 和来源清单为准。发布页为 https://github.com/alatorrerebecca240-ship-it/WDIEmbedded-Trainer-/releases/tag/knowledge-v1.1.0 。

## Python

Python 3.13.15 Windows x86-64 完整安装器来自 Python Software Foundation，未修改。发行包构建时核对 SHA-256 和官方 Authenticode 签名；安装时与 VSIX 内固定 SHA-256 比对，不需要联网查询证书撤销服务。许可证副本见 `Python-LICENSE.txt`，安装器与安装后的目录还包含相应第三方组件条款。

- 官方发行页：https://www.python.org/downloads/release/python-31315/
- 安装器：https://www.python.org/ftp/python/3.13.15/python-3.13.15-amd64.exe
- 对应许可证：https://github.com/python/cpython/blob/v3.13.15/LICENSE

## C 与 C++ 编译器

LLVM-MinGW `20260826` UCRT x86_64 版本原始 ZIP 来自项目官方 GitHub Releases。它是 LLVM/Clang、MinGW-w64、相关运行库及辅助工具的组合，各组件许可证不同，不能只按插件的 MIT 处理。完整原始归档中的 LICENSE、COPYING、NOTICE 等记录保持不变；提取出的许可文件副本也放在 `compiler` 子目录。再分发时请保留归档与相应条款。

辅助工具包含 BusyBox-w32、GNU Make 和 gendef 等。对应源码、固定提交与构建配方保存在整体包的 `sources` 目录；它们不需要学员执行。`sources/source-manifest.json` 记录版本与校验值。再分发完整离线包时请同时保留这些源码及构建材料，不要只留下二进制工具。

- 官方源码与构建说明：https://github.com/mstorsjo/llvm-mingw
- 固定发行版：https://github.com/mstorsjo/llvm-mingw/releases/tag/20260826

此工具链用于 Windows 电脑端的 C11/C++17 练习，不是单片机固件交叉编译环境，不包含芯片厂商 IDE、驱动或烧录工具。

## Boost

Boost 1.85.0 原始 ZIP 来自 Boost 官方归档，使用 Boost Software License 1.0。副本见 `Boost-LICENSE_1_0.txt`；原始 ZIP 内的许可与其他版权文件均保留。插件仅解压 `boost/` 头文件和根许可证，不安装源码示例或运行第三方测试。它是部分 C++ 拓展题的依赖，基础训练可先不安装。

- 官方归档：https://archives.boost.io/release/1.85.0/source/boost_1_85_0.zip
- 归档校验记录：https://archives.boost.io/release/1.85.0/source/boost_1_85_0.zip.json

## 使用边界

VS Code 本体没有放入本包，请预先从官方渠道安装。软件安装确认和知识包代码信任是两项独立授权；安装环境不会自动授权执行任何题库代码。SHA-256 用于核对文件是否一致，并不证明任意题目代码安全。使用者仍应核对发布者与题库来源。
