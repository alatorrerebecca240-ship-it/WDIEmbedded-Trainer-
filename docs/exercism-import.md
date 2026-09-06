# Exercism 批量获取：先做可靠母题，再扩展变式

## 本轮交付与边界

- 原生 VS Code 维护者菜单：扫描 → 筛选 → 多选 → 导入草稿 → 静态检查。
- 首批 32 个不同题目：24 C、8 C++，25 入门、7 进阶；不把同题多语言版本算成独立母题。
- 按 Git 全长提交固定官方 C/C++ 仓库，通过 Git blob 校验下载；包内每个原文件另记 SHA-256，保留原始测试、参考代码和许可证。
- 生成统一 `programming` 草稿。选择、判断、代码阅读、纠错及 AI 变式继续使用已有模板/生成链路；本轮不会机械地把每个代码文件包装成多道“新题”。
- 中文标题、目标、知识点已经加入，完整英文题面保留。中文题干精校、初始接口补齐及参考答案/初始失败的 Docker 验证尚待审核。
- 下载成功不等于可练习或可发布。不要把 `knowledge/drafts` 加入 `trainer-packs.json`；已有基础包和私人答案不改变。

## 插件操作

课程树“…” → **批量获取开源题目**，或“管理知识包” → “维护者：批量获取开源题目”。支持 C/C++ 分类、入门筛选和知识点搜索，每批最多 50 题。导入失败不会替换已有包；已下载的缓存可在重试时复用。

工作区 `knowledge/drafts/名称/` 保存草稿，`.imports/exercism-index.json` 保存扫描目录，`.imports/exercism-cache/` 保存源码缓存，`.trainer/authoring/` 保存静态报告。缓存目录可离线浏览；未下载的源码仍需要网络。草稿和缓存默认被 Git 忽略；正式发行只走人工审核流程。

## 可复现的首批题目

固定来源：

- `exercism/c`：`2e8a0022fd2a611adc08b4d6e70d07b988cc5364`
- `exercism/cpp`：`413b80a9b94089e4588c50500b8553a59c48cda8`

题目选择和中文目标由 `trainerlib/exercism_curriculum.py` 维护。维护者备用命令（插件用户无需输入）：

```text
python scripts/import-exercism-pilot.py
python trainer.py packs audit knowledge/drafts/exercism.pilot --runner none --report .trainer/authoring/exercism.pilot.audit.json
```

第一个命令在干净检出中重新下载固定提交并生成试点，已有同名目录会拒绝覆盖。第二个只做静态检查；32 道编程题缺少执行证据，因此预期退出 1、`passed=false`，不能据此批准发布。

## GitHub Actions Docker 验证

将本轮工具、测试和 `.github/workflows/exercism-pilot.yml` 推送到主分支后，打开 Actions → **Import and verify Exercism pilot (draft only)** → **Run workflow**。

工作流使用固定来源重建草稿，然后验证参考代码通过、初始代码能编译但测试失败。只读权限、不保留 Git 凭据；代码仅在无网络、只读文件系统、非 root、禁用权限提升并设定资源上限的 Docker 容器运行。下载不执行上游构建脚本。失败时仍上传已有报告和草稿供检查，不自动审批、打发布包或部署 Pages。

该工作流只检查固定试点，不读取本地任意新建草稿。后续人工适配后的草稿需显式提交选定目录，使用现有 `review-draft.yml` 指定路径审核。不能把初始代码编译失败当成合格的“测试失败”。审核通过后才进入既有批准、再次验证、Release 和 Pages 发布流程。

Docker 单次 C 编译和测试限 256 MiB / 60 秒，C++ 限 768 MiB / 90 秒（完整 Catch2 编译需要更高内存预算），两者均限 1 CPU、64 个进程和 64 MiB 临时空间；题目不能自行扩大这些限制。本地未运行 Docker，这些限额的实际适用性以 Actions 报告为准。

## 许可与安全

Exercism 题目/参考代码保留 MIT；C 的 Unity 保留内嵌 MIT 版权声明。C++ Catch2 单独记录 BSL-1.0 来源和完整许可，不被项目 MIT 覆盖。`origin.dependencies` 采用独立、扁平的来源记录，逐项验证许可证、固定提交及留存哈希；要求最低引擎 0.8.0。

导入器只支持官方 `exercism/c`、`exercism/cpp`，拒绝符号链接、子模块、路径穿越、无法映射的源码布局及不识别的忽略测试语句。保留原测试并启用原来忽略的 C 测试/C++ 扩展测试，不执行上游脚本。未来上游结构或许可变化需要人工复核，静态许可检查不能替代人的版权审阅。

网络访问使用 HTTPS 和主机白名单；目录摘要用于检测意外修改，不是发布者数字签名。GitHub API 限流/连接失败时保留上次完整目录，不修改 DNS、代理或 TLS 校验。
