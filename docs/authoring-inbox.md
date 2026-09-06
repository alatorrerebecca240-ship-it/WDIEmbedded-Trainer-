# 一键获取 + 集中审核（0.9.0）

## 日常操作

在 VS Code 的课程视图“…”或“管理知识包”打开 **获取新题** 与 **集中审核**。普通练习者仍使用“更新题库”，不参与维护流程。

获取新题会接管旧 Exercism 草稿，自动筛选入门/进阶题、排除已存在 ID 和同源母题、检查相似题干，每轮最多尝试 20 个新题。采用每题独立的临时目录与审核包，一题失败不影响其他题。扫描失败用完整缓存；缺失源码仍需网络。原始批次不删除、不修改。

集中审核按状态展示每道题及问题，可浏览完整题面、starter、reference、tests、许可证、来源和执行报告。只对已具备匹配 Docker 证据的题开放人工批准；批量勾选默认不全选，并要求审核人及明确内容/版权确认。失败题可暂缓或恢复重试，不自动进入正式课程。

## 一次性云端配置

1. 将 0.9.0 工具、测试和 `.github/workflows/acquire-review.yml` 推送到目标仓库的 main。
2. 在用户级 `embeddedTrainer.authoringRepository` 配置 `owner/repo`，默认本项目仓库。工作区不能覆盖此设置。
3. 首次自动验证时确认发送范围，并通过 VS Code GitHub 登录授权。插件使用 VS Code 官方认证接口，会话令牌仅用于 `api.github.com` 请求，不写入参数、日志、工作区或队列。[VS Code 认证 API](https://code.visualstudio.com/api/references/vscode-api#authentication)
4. 后续“获取新题”自动提交等待题目；未配置、取消授权或网络失败时保留本地收件箱，配置好后点“重新验证待处理题目”。工作流调度需要相应仓库权限，GitHub OAuth 调度接口使用 `repo` scope。[GitHub 工作流调度 API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)

每个云端任务最多 50 题，更多待办再次点击重新验证。每次任务有唯一请求 ID，发送前持久化；POST 响应丢失时按请求名寻找原任务，不盲目重复提交。VS Code 运行期间每分钟检查任务，退出后不运行后台程序，重开恢复检查。状态不变时静默；验证完成或需要处理时通知。

## 内容与云端证据如何对应

- 未编辑题目：发送公开上游题目标识、全长提交和规范化包指纹；Actions 下载重建。界面不上传本地源码或私人答案。
- 本地已编辑题目：旧证据失效。先显式提交并推送该单题草稿，再点重新验证；计划只携带严格限定的草稿路径及新指纹，Actions 读取同一工具提交中的文件。缺失或不一致就拒绝验证。
- `knowledge/drafts/` 默认忽略，只有明确选择的编辑草稿才应纳入 Git。不得把 `.trainer/`、`exercises/` 或凭据推送到公开仓库。
- 校验任务所属仓库、工作流、事件、请求名和工具提交；只接受对应任务的唯一未过期报告附件。下载重定向不携带 GitHub 令牌，拒绝非白名单下载域。
- 先对 ZIP 校验 GitHub 给出的 SHA-256，再只读一个大小受限的 `inbox-results.json`，从不解压任意路径。随后检查请求摘要、完整题目集合、每题指纹和原有 Docker 审核门禁。[GitHub Artifact API](https://docs.github.com/en/rest/actions/artifacts)

Actions 不运行上游构建脚本；参考答案和初始代码仅在既有无网络、只读挂载、非 root、受资源限制的 Docker 容器执行。每题独立验证，部分失败仍可生成其他题的成功证据。**工作流绿色仅表示结果完整生成，不代表所有题通过。**题目修改、旧报告、错误编译、缺少初始代码有效失败证据，都不能当作审核通过。

本地报告与人工批准不是数字签名；正式发布仍重新运行原有验证，不靠本地报告绕过门禁。

## 审核与发布分开

人工审核通过只写对应包的内容绑定 `review.json`。之后“准备发布已审核题目”再次确认，生成 `knowledge/approved/` 快照；不覆盖已有不同指纹的快照，不提交 Git、不创建标签、不发布 Release。推送、版本选择以及现有发布工作流的再次验证和环境审批仍需维护者明确执行。

已经进入发布快照的题目不能用“暂缓”偷偷撤销；撤回或发修订版应单独处理。

## 位置与开发验证

| 位置 | 用途 |
| --- | --- |
| `knowledge/drafts/inbox/review.exercism.*` | 逐题规范化草稿；旧批次原样保留 |
| `.trainer/authoring/inbox.json` | 集中审核状态，不公开 |
| `.trainer/authoring/requests/`、`evidence/` | 请求绑定和云端证据，不公开 |
| 插件全局存储的 `authoring-downloads/` | 已校验的报告 ZIP，不使用草稿提供的下载路径 |
| VS Code workspaceState | 待跟踪任务、一次性授权选择和审核人；不保存令牌 |
| `knowledge/approved/` | 明确确认后生成的发布快照 |

CLI 备用入口为 `packs inbox-get/list/details/plan/results/decide/stage`。正常界面操作不需要 PowerShell。写队列时持有排他锁并原子保存；若进程异常崩溃，先确认没有导入进程，再检查 `.trainer/authoring/inbox.lock`，不要在另一个任务执行时删除锁。

测试使用合成上游文件、模拟 GitHub API/认证、模拟 Docker 参数，覆盖重复获取、部分失败、人工确认、源文件修改、旧报告、身份/哈希不符和下载安全。本地测试通过不代表已在用户仓库实际运行 Actions；远程部署与首次授权是独立的一次性步骤。
