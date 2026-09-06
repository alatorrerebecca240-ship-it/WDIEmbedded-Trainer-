# 知识包：获取、审核、发布与多电脑使用

本功能从 0.6.0 开始提供。学习者在 VS Code 界面操作；以下命令面向题库维护者，均在项目根目录运行。Python 核心只用标准库，不需要数据库或自建服务器。

## 目前做到哪里

- 原来的 198 道题已无损导出到 `knowledge/packs/foundation.core/`，仍然可本地练习。题目 ID 不变，旧答案和进度保留。
- 已从五个上游项目下载固定提交的选定源码、测试和许可证，转换出 14 道草稿；另有 20 道参数化 C 代码阅读草稿。草稿不会自动混入正式课程。
- 获取、转换、参数化生成、本地 Ollama 接口、发布门禁、离线安装、自动更新、回退及 GitHub 工作流均已实现。
- **尚无已审核知识包发布**：目标仓库为 `alatorrerebecca240-ship-it/WDIEmbedded-Trainer-`，原创内容已选择 MIT，旧基础包的编程参考实现尚未全部补齐。本机没有运行第三方草稿的参考代码；执行验证按约定交给 GitHub Actions Docker。
- Ollama 接口经过模拟响应测试，但此电脑尚未配置本地模型，未把“接口可用”当作“AI 题目正确”。

## 数据与程序分离

```text
knowledge/sources.json + recipes/      选定上游文件和声明式转换规则
              ↓ 固定 commit + SHA-256，保留许可证
.imports/ → knowledge/drafts/         未审核，不参与学习和发布
              ↓ 人工内容/版权检查 + Actions Docker 验证
knowledge/approved/                  只接收与审核指纹一致的快照
              ↓ 发布时再次验证，生成 ZIP + SHA-256
GitHub Releases ← catalog.json → GitHub Pages
                                ↓ HTTPS 清单、版本与校验
VS Code 插件 → 不可变版本缓存 → 本地练习与进度
```

题库格式不依赖 VS Code API；可单独维护在公开 GitHub 仓库。当前目录结构是单仓库开发布局，插件打包时只带 `trainer.py`、`trainerlib/` 和 UI，不包含 `knowledge/`、`content/`、答案、进度或导入缓存。若另建专门的题库仓库，应同时放入审核/发布所需的工具、schemas 和工作流，或固定引用它们的已审核版本；不需要放入 VS Code 插件源码。

| 位置 | 保存什么 | 是否应公开 |
| --- | --- | --- |
| `knowledge/packs/foundation.core/` | 当前本地可编辑基础包 | MIT 源码，可公开；不代表已通过知识包发布审核 |
| `knowledge/drafts/` | 导入或生成的未审核草稿 | 默认忽略；仅显式提交选中的审核草稿 |
| `knowledge/approved/` | 已人工审核的发布快照 | 是 |
| `.imports/` | 固定提交的上游缓存、原文件哈希 | 默认不提交 |
| `exercises/`、`.trainer/progress.json` | 个人代码和学习记录 | 不提交到公开题库 |
| VS Code 全局存储的 `knowledge/` | ZIP 缓存、历史版本、安装索引、代码信任记录 | 本机私有 |

`trainer-packs.json` 的 `sources` 配置本地源码包，路径相对工作区；`legacyContent: false` 停止重复读取旧 `content/`。旧目录保留兼容，不是当前题目的编辑入口。同 ID 的已安装知识包优先于可编辑源码包；不同包的题目 ID 不允许冲突。本地源码包属于你已信任的工作区，不能把未审查草稿直接加入 `sources` 后批量运行。

## 统一格式

一个包至少有 `pack.json` 和 `questions.json`，可带 `lessons/`、`licenses/`、`upstream/`。正式 ZIP 在根目录直接放这些文件，不再套一层文件夹。

```json
{
  "formatVersion": 1,
  "id": "my.c-basics",
  "version": "1.0.0",
  "title": "C 语言入门",
  "minEngineVersion": "0.6.0",
  "license": "LicenseRef-Pending"
}
```

`questions.json` 是 `{"formatVersion":1,"questions":[...]}`，每道题保存完整字段，不依赖隐式 defaults。完整规范见 `schemas/knowledge-pack.schema.json`、`schemas/normalized-questions.schema.json` 和 `schemas/lesson.schema.json`。可直接参考已有 recipes 和模板。

题目共有六种类型：`single-choice` 选择、`true-false` 判断、`fill-blank` 填空、`code-reading` 代码阅读、`debugging` 纠错、`programming` 编程。选择/判断/填空不执行题干中的命令。代码阅读在发布时编译完整的 C/C++ `main` 程序验证输出，学习时仅提交答案。编程和纠错的 `reference/` 与 `starter/` 保持同样的源码布局，使用同一套 `tests/`。

题目共同字段包括 ID、标题、学习方向、语言、难度、概述、知识点、提示、先修条件、目标和 `origin`。来源记录包含许可证、许可证/NOTICE 文件、上游仓库、完整 commit、保留源码路径和 SHA-256、改编说明。变式增加 `variantOf`、`parameters` 和生成器来源；AI 无权改写来源授权。

同一版本不能换内容重新发布；任何题干、答案、测试、参考代码、来源或许可证改动都会使原审核失效。新增或修订后应提升 `MAJOR.MINOR.PATCH` 并重新审核。不要用同一道题的 ID 改成完全不同的知识点或题型；课程移除后需要回退旧包才能继续打开旧题。

`.gitattributes` 对 `knowledge/**` 关闭换行自动转换，以便 Windows 本地、GitHub 提交和 Linux CI 对同一快照计算相同哈希。不要在审核后自动格式化或转换这些文件；确实要修改时重新审核。

## 获取与转换第三方内容

默认不是全站爬虫，也不会从任意教学网站抓题。`sources.json` 列出精确允许获取的路径，每批最多 100 个 UTF-8 文件，每文件最多 2 MiB；可分批增加配置。解析分支时首先固定完整提交 SHA，随后下载该提交下的文件，不执行上游脚本。

| 来源配置 ID | 当前选取范围 | 授权依据与边界 |
| --- | --- | --- |
| `exercism-c` | C leap 的头文件、参考实现和测试 | [Exercism C LICENSE](https://github.com/exercism/c/blob/main/LICENSE)，MIT |
| `opendsa-code` | C++ 插入排序、冒泡排序源码 | [OpenDSA MIT-license.txt](https://github.com/OpenDSA/OpenDSA/blob/master/MIT-license.txt)，仅所选代码；不能推断整本书和图片都为 MIT |
| `zephyr` | blinky 示例 | [Zephyr LICENSE](https://github.com/zephyrproject-rtos/zephyr/blob/main/LICENSE)，Apache-2.0，仍逐文件查 SPDX |
| `freertos-kernel` | task/queue 公共头文件 | [FreeRTOS Kernel LICENSE.md](https://github.com/FreeRTOS/FreeRTOS-Kernel/blob/main/LICENSE.md)，MIT |
| `cmsis6` | CMSIS-RTOS2 API 头文件 | [CMSIS_6 LICENSE](https://github.com/ARM-software/CMSIS_6/blob/main/LICENSE)，Apache-2.0；不扩大到所有厂商 SDK |

```text
python trainer.py packs fetch --source all --output .imports
python trainer.py packs fetch --source exercism-c --ref FULL_40_CHARACTER_COMMIT --output .imports
python trainer.py packs import --source .imports/exercism-c-COMMIT --recipe knowledge/recipes/exercism-leap.json --destination knowledge/drafts/exercism.leap
```

把占位的 COMMIT 换为 fetch 输出的目录名。已有目录不覆盖；相同 commit 的选取范围变动时使用新的 `--output`。其他 recipe 同理。当前适配器通过声明式 JSON 映射上游文件，再添加中文题干、选项和解释；**不是任意源码自动变成正确题目的万能转换器**，新 API/题目族需要维护新的 recipe。

Exercism 示例包含全部六种题型；编程和纠错保留了上游测试，附加一个小型宏适配层运行这些断言，不声称复刻完整 Unity 框架。Zephyr/FreeRTOS/CMSIS 示例当前先转换成概念客观题，不在本机编译或运行硬件固件。

## 参数模板与本地 AI

```text
python trainer.py packs generate --template knowledge/templates/c-modulo.json --destination knowledge/drafts/my-modulo --count 20 --seed 42
python trainer.py packs ai knowledge/drafts/my-pack --question my.question-id --model YOUR_LOCAL_MODEL --count 3
```

模板使用 `${变量}`，整数有限集合和受限四则运算，不使用 `eval`。同一模板、seed 和参数生成结果可复现；生成失败不留下半个目标包。变式族可以豁免部分文本相似度告警，但完全相同题干/代码仍会拦截。

AI 只连接字面回环地址 `http://127.0.0.1:11434` 或 IPv6 `::1`，禁止远程 endpoint、代理转发和重定向；已知 cloud 名称拒绝使用。请在启动 Ollama 服务时设置 `OLLAMA_NO_CLOUD=1`、重启并确认日志，再选已经下载的本地模型。仅访问回环地址不能证明一个自行代理的服务没有联网。详见 [Ollama 本地模式说明](https://docs.ollama.com/faq#how-do-i-disable-ollama-cloud-features)。工具不会自动安装软件或下载模型。

AI v1 支持选择、判断、填空和代码阅读的草稿变式；涉及文件的编程/纠错先用受控模板与 recipe。保存前检查基本格式，后续仍必须检查答案、难度、版权和重复度。AI 不会自动批准草稿。

## 发布门禁与安全边界

1. 格式：必填字段、合法题型、答案、语言标准和安全的资源路径。
2. 来源：明确 SPDX、保留许可证/NOTICE、完整 commit、原文件哈希、改编记录；未知授权、`project-license` 和 `LicenseRef-Pending` 禁止发布。
3. 重复：包内与同批发布包间查重复/近似文本，同时检查全局 ID 冲突。相似度只是辅助，非语义正确性证明。
4. 答案：代码阅读的显示代码必须与被验证代码一致，实际输出匹配答案；编程/纠错参考实现必须通过全部测试，初始代码必须能编译且测试失败。
5. 人工：审核人确认内容和版权，对整个包内容 SHA-256 留下绑定记录。许可证文字是否充分、组合许可是否兼容、选择题是否只有一个正确项，都需要人工判断。
6. 打包：再次运行检查；产生可重复的 ZIP、`.sha256` 和审计 JSON。编译器镜像可能随 `gcc:14` 更新，并不承诺任意工具链上的测试结果完全一致。

```text
python trainer.py packs audit knowledge/drafts/my-pack --report .trainer/audit.json
```

默认只做静态检查。有可执行参考答案但未执行时报告失败，这是预期门禁，不会擅自在本机运行。

GitHub Actions 的 Docker 使用无网络、只读代码挂载、只读根文件系统、非 root 用户、去除 capabilities、禁提权、CPU/内存/PID/运行时间/输出量限制。容器不挂载宿主 home、凭据或 Docker socket。Docker 不是对任意恶意程序的绝对安全保证，仍应先人工审查输入，使用临时 GitHub 托管 runner，不要改成有私人资料的 self-hosted runner。

客户端安装只读数据，不编译或运行代码。安装校验拒绝目录穿越、软链接/重解析点、Windows 保留名、大小写冲突、压缩炸弹、脚本/二进制资源。SHA-256 是完整性校验，**不是发布者签名或代码安全证明**。只添加你信任的清单来源；将来需要签名和密钥轮换可扩展目录格式。

## 配置 GitHub：采用 Actions Docker 审核

用户已创建公开仓库 [alatorrerebecca240-ship-it/WDIEmbedded-Trainer-](https://github.com/alatorrerebecca240-ship-it/WDIEmbedded-Trainer-) 并选择 MIT。根 LICENSE 沿用远端现有版权声明；基础题和新模板/改编文字使用 MIT，Zephyr/CMSIS 上游仍为 Apache-2.0，相应混合包标为 `mixed`。现有未审核草稿不会被这次选择自动批准，应使用更新后的 recipe/template 重新导入生成。第三方授权必须保留，不能通过根 MIT 文件覆盖。

1. 使用上述已存在的公开仓库，默认分支为 `main`。上传前检查 `.gitignore`，不要上传个人 `exercises/`、`.trainer/`、凭据或整个下载缓存。本机特定编译器路径和编辑器设置也已排除；其他电脑自行配置 Python 与编译器。
2. GitHub Settings → Pages → Source 选 **GitHub Actions**。
3. Settings → Environments 建立 `knowledge-release`，设置所需审核人和受保护的发布标签；保护 `main` 的代码审查。不要给程序验证 job 注入 secrets。
4. 为选中的草稿补齐原创授权、许可证文字、测试和参考实现。`knowledge/drafts/` 默认被忽略，需要在 VS Code Git 界面或 `git add -f knowledge/drafts/选中的包` **显式只提交该包**。不要提交缓存或所有私人草稿。
5. 在 Actions 手动运行 **Verify draft references in Docker**，输入已提交的 `knowledge/drafts/my-pack`。程序在 Docker 中执行。修复全部错误，确认该次 run 对应自己审阅的提交，下载 `draft-audit` artifact 内的 `draft-audit.json`。
6. 本地保持完全一致的文件，核对报告来自可信工作流，再记录自己的人工审核：

```text
python trainer.py packs review knowledge/drafts/my-pack --reviewer YOUR_GITHUB_NAME --ack-copyright --ack-content --verification-report draft-audit.json
python trainer.py packs promote knowledge/drafts/my-pack --destination knowledge/approved/my-pack
```

本地不会因此执行第三方代码。报告必须通过、标明 Docker、覆盖所有可执行题且内容指纹吻合。下载报告不是密码学签名，仅供人工确认；正式构建不能用报告跳过再执行。`promote` 目标已存在时拒绝覆盖，更新已有批准包应在分支中有意识地提交新版本和新审核记录。

7. 提交 `knowledge/approved/` 的审阅快照到 `main`，创建并推送 `knowledge-v1.0.0` 这样的标签（或手动指定已有标签）触发 **Publish reviewed knowledge packages**。只有成功经过全部包检查后才上传 artifact，之后独立的写权限 job 创建 Release，再部署 Pages。
8. `knowledge/approved/` 为空或任何一个包未通过时，发布失败且不生成对外 Release。不要把未授权的整个基础包直接搬进去。Release 已存在时不覆盖；失败重试若 Release 已建立，应检查资产后使用新发布标签，不强行覆盖已发布字节。
9. 发布成功后，在插件的“管理知识包”添加 `https://alatorrerebecca240-ship-it.github.io/WDIEmbedded-Trainer-/catalog.json`，浏览并安装需要的包。这是预期地址，Pages 成功部署前不可用。每次清单包含该发布批次的全部批准包，历史 ZIP 留在旧 Releases。

工作流 action 固定到提交 SHA。验证 job 无写权限，发布 job 不 checkout 或执行题目代码。需要持续维护这些 action 和编译器镜像版本，不能把当前固定版本当作永久安全承诺。

公开仓库的常规 GitHub 托管 runner 使用和 Pages 可利用免费方案，但不是无限资源；避免付费大型 runner、私有仓库超额使用和频繁无效构建。Pages 只放小清单，ZIP 放 Releases。本客户端另设每包 32 MiB 压缩/128 MiB 展开上限。资源政策以 [GitHub Actions 计费](https://docs.github.com/en/actions/concepts/billing-and-usage)、[Pages 限制](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)、[Releases 说明](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases) 为准。

## 学习者：无需终端的多电脑使用

1. 在另一台电脑安装 0.6.0 VSIX 和 Python 3.9+；只有编程评测需要 GCC/G++ 或兼容编译器。纯知识题不要求 Linux/ROS 2/Docker。
2. 打开用于练习的文件夹，或不打开文件夹由插件使用私有练习目录。无需克隆项目源码，插件自带 Python 引擎，但不内嵌题库。
3. 点课程树上方包图标 → 添加可信清单 → 浏览并安装。退出 VS Code 后没有后台守护进程；运行期间默认每 24 小时检查一次，也可手动检查。
4. 若要在多台电脑订阅相同题库，启用 VS Code Settings Sync 的设置同步。同步的是清单地址和选中包 ID，各电脑自行下载，不同步缓存、编译器路径、代码信任、练习答案或学习进度。VSIX 若未在 Marketplace 发布，应在每台电脑手动安装。
5. 离线时选择“离线导入 ZIP”，粘贴从可信发布页或单独的 `.sha256` 文件取得的哈希。断网仍可做已经安装的题。
6. 出现内容问题，选择“回退到已保留版本”。回退会暂停该包自动更新；之后可手动恢复。不会覆盖个人练习文件，也不会删旧缓存。
7. 下载的编程包默认不能在本机执行，须先看过代码，在管理菜单选择“信任知识包代码”。信任只对应当前 ZIP 的哈希，新版本需再次确认。选择/判断/填空/阅读作答不要求这个授权。

离线安装默认没有远程来源绑定。如果可信清单中有与该离线版本完全一致的 ID、版本和哈希，可在“浏览并安装”显式选择同一包，建立订阅；不会仅凭相同包 ID 让其他来源接管它。

已有练习记录创建时的包版本，评测继续使用缓存的旧版本，不把新测试悄悄覆盖进去。原有未带版本的旧练习保持兼容；可编辑源码包变动而旧快照不在缓存时会提示你备份/另开练习。包内旧题被新版本删除时，先回退旧包再打开它。

插件缓存可从“管理知识包 → 打开版本与缓存目录”定位：`versions/包ID/版本/` 是解包内容，`cache/哈希.zip` 是离线 ZIP，`installed.json` 是原子切换的活动版本索引。CLI 默认另用项目 `.trainer/knowledge/`，可通过 `TRAINER_PACK_HOME` 指向同一目录；不要同时手工编辑安装索引。若上次进程异常留下 `install.lock`，先确认对应进程已退出再清理这一锁文件，不要删除整个知识库。

## 开发验证

```text
python trainer.py validate
python -m unittest discover -s tests -v
npm --prefix apps/vscode-extension run check
npm --prefix apps/vscode-extension test
```

自动测试使用临时目录、自写的小型 C/C++ 固件模型/fixture 和模拟网络，不执行五个上游草稿、不修改个人学习目录。GitHub/实际 Docker 和实际 Ollama 的联调需要配置相应服务后再完成。
