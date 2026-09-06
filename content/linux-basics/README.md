# Linux 基础

32 题：2 道 C 编程题、12 道选择题、9 道判断题、9 道填空题。其中 27 道入门、5 道进阶。

## 学习顺序

1. 路径与目录：pwd、cd、绝对/相对路径、主目录、. 与 ..。
2. 文件与文本：ls、cp、mkdir、grep、tail、man、含空格的文件名。
3. 权限与安全：r/w/x、chmod、目录权限、sudo 的使用边界、删除风险。
4. Bash 数据流：标准输入/输出/错误、管道、追加与覆盖、退出状态、&&。
5. 环境与进程：PATH、export、source、ps、SIGTERM。
6. 配套编程：权限位转字符串、统计路径片段。

在 VS Code 的 Embedded Trainer 课程树中展开“Linux 基础”，选择题型即可学习；每题有提示，答对后展示解析。

## 环境与安全边界

- 知识题只检查提交的答案，无需 Linux、WSL 或虚拟机。插件后台仍需要 Python。
- 命令知识按 Linux + Bash + 常见 GNU 工具讲解，不按 PowerShell、CMD 或所有 Unix shell 的规则讲解。
- 命令名称与环境变量按实际大小写判定；填空只填写题目要求的片段，不附带提示符。
- 题干不自动执行。真正尝试命令时，应先用个人临时目录和示例文件，确认路径、权限与参数。
- 常规 rm 不保证可恢复；重定向 >、2> 及同名复制都可能覆盖文件；不要在重要目录尝试破坏性操作。
- 两道编程题只处理传入的数字/字符串，不改权限、不访问真实文件系统，在现有 Windows C 编译环境也能完成。

## 维护与扩展

客观题保存在本目录的 question-bank.json；编程题分别位于 permission-triplet 和 path-components。追加知识题时保持 ID 唯一，使用 language: text、入门优先的难度标签和原创解析。格式说明见 ../../docs/adding-a-lesson.md。

## 官方参考

以下文档用于核对基础规则，题干、选项与教学代码为本项目编写，不是复制整套外部试题。

- [GNU Coreutils：路径、文件、文本与权限命令](https://www.gnu.org/software/coreutils/manual/coreutils.html)
- [GNU Bash：管道](https://www.gnu.org/software/bash/manual/html_node/Pipelines.html)
- [GNU Bash：重定向](https://www.gnu.org/software/bash/manual/html_node/Redirections.html)
- [GNU Bash：退出状态](https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html)
- [GNU Bash：内建命令（含 . 与 export）](https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html)
- [GNU Bash：作业控制内建命令（含 kill）](https://www.gnu.org/software/bash/manual/html_node/Job-Control-Builtins.html)
- [GNU Grep：文本匹配](https://www.gnu.org/software/grep/manual/grep.html)

进阶题仅涉及基础概念的组合，不包含内核驱动、复杂进程间通信或系统管理员实战。
