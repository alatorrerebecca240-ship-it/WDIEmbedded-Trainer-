# 架构

0.6.0 已把内容、执行和编辑器集成分开。完整发布与消费协议见 [知识包工作流](knowledge-pack-workflow.md)。

```text
GitHub Pages catalog → Releases ZIP → trainerlib.store（缓存/版本/回退）
                                           |
本地源码知识包 → trainerlib.runtime → trainer.py catalog → VS Code UI
                                           |
                                  exercises + progress.json
```

## 设计边界

- `knowledge/packs/`：本地可编辑课程源；现有基础包 ID 保持不变。
- `knowledge/drafts/`：来源锁定但尚未人工审核的素材转换/生成结果，不参与默认训练。
- `knowledge/approved/`：供 CI 再验证并发布的审核快照。
- `content/`：旧格式兼容来源，当前配置关闭其加载以避免重复。
- `exercises/`：学习者的工作副本，框架不会自动覆盖。
- `.trainer/`：本机生成的构建产物和学习进度，不提交版本库。
- `trainer.py` + `trainerlib/`：与编辑器无关的执行核心、格式校验、获取/生成、审核与安全安装工具。
- `.vscode/`：快捷入口；删除后 CLI 仍能工作。
- `apps/vscode-extension/`：可选的图形界面，不拥有课程和构建规则。

## 后续扩展点

1. 在 `trainer.py` 外提取 runner 接口，加入 PlatformIO、CMake、厂商 CLI 和串口测试适配器。
2. 将公开测试与教师端隐藏测试分开。
3. 增加硬件在环协议，例如从串口读取 JSON 测试结果。
4. 在已有版本、来源、许可证和最低引擎版本字段之上，扩展签名、密钥轮换及知识包依赖解析。
5. 将本地 JSON 进度替换为可选的 SQLite 或同步服务。
