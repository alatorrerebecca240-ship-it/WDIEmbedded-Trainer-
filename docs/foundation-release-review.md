# 首个知识包发布准备：foundation.core 1.0.0

2026-09-06：仓库所有者明确审核通过后，已发布 [knowledge-v1.0.0](https://github.com/alatorrerebecca240-ship-it/WDIEmbedded-Trainer-/releases/tag/knowledge-v1.0.0)，[完整发布流程](https://github.com/alatorrerebecca240-ship-it/WDIEmbedded-Trainer-/actions/runs/34013079842)已成功完成。首发范围固定为现有 198 道基础/进阶题，不包含 knowledge/drafts 中的第三方导入或批量生成草稿。

[审核记录与原始机器报告](../knowledge/reviews/foundation.core-1.0.0/README.md)长期保存在仓库中，批准的原字节快照位于 knowledge/approved/foundation.core。包内 README 保留其送审时的文字；是否批准以绑定内容指纹的 review.json 和实际发布记录为准。以下保留准备和审核步骤，供后续版本参考；不能将本次确认用于批准修改后的快照。

## 本次准备内容

- 27 道编程题都有单独的 reference/，保持 starter/ 未完成状态。
- 覆盖 C、C++、嵌入式、智能车、电设、Linux 基础和 ROS 2 基础；模型题不依赖开发板或 ROS 2 运行时。
- 修复六处浮点测试对 NaN 的误接受，补充回调空指针、单元素缓冲区、采样归一化、ADC 舍入、PID 状态和整数边界测试。
- 69 道选择、53 道判断、49 道填空题的既有答案与解析没有在本次改写，已随本次快照获审核者确认；后续修改须重新审核。
- 全包使用已选定的 MIT，保留 licenses/MIT.txt；不借根许可证覆盖任何第三方授权。

## 自动验证与查看材料

推送该包或审核工具的改动到 main，会启动 **Verify draft references in Docker**。也可在 Actions 页面手动运行，pack 填 knowledge/packs/foundation.core。

每道编程题分别编译并运行参考答案和 starter：前者必须通过，后者必须编译成功且测试失败。使用 GitHub 托管 Linux runner，容器内禁止网络、只读挂载、非 root 及资源限制。不会批量在维护者电脑原生运行这些新参考答案。

打开对应 Actions run，先确认提交 SHA，再下载 draft-audit artifact：

- draft-audit.json：内容 SHA-256、机器校验结果、逐题执行完成清单。
- draft-review.md：绑定同一指纹，列出全部题干、答案、解析、参考实现、测试以及该提交的源文件链接。

完整查看后勾选审核材料中的人工检查项。机器报告只证明该快照通过了当前检查，不证明全部题意、版权声明或工程适用性都正确。脚本不会填写 review.json，不会替任何人批准发布。

仅在本地生成待审材料（不执行包内程序）：

```text
python trainer.py packs audit knowledge/packs/foundation.core --report .trainer/foundation-static-audit.json
python scripts/draft-review-sheet.py --pack knowledge/packs/foundation.core --report .trainer/foundation-static-audit.json --output .trainer/foundation-review.md
```

第一个命令在尚未执行参考答案时会按预期返回失败；不要把静态报告用于批准。报告和材料必须位于包目录之外，防止改变被审核的内容指纹。

## 审核者明确批准后才做

由具名审核者确认准确版本的内容与授权，并使用可信 Actions run 下载的报告记录审核，再 promote 到 knowledge/approved。具体命令、Pages 设置和发布标签见 [完整发布流程](knowledge-pack-workflow.md#配置-github采用-actions-docker-审核)。

正式发布会再次执行 Docker 校验；本地审核报告不能绕过它。Pages 清单只有 Release 资产成功创建后才部署。在这之前，不应在其他电脑上把本包当作已审核发布版安装。

本次不改动 exercises/、学习进度、个人编译器配置或已安装插件，也不将这些私有内容上传 GitHub。

## 首发上线验收

2026-09-06 使用插件共享的 PackStore 客户端，从真实 Pages 清单下载并安装正式 Release ZIP，测试只使用一次性临时目录。

- 线上清单可读，包为 foundation.core 1.0.0，共 198 题。
- ZIP 大小 107985 字节，SHA-256 为 `5405c047cafdfccf6bf750ce81e931045df25b9eeb825e2e04205e50842cf081`，与清单和 Release 资产摘要一致。
- 161 个包内索引文件逐个验证；内容指纹与人工批准快照一致。
- 缓存清单读取、断网条件下离线 ZIP 导入均通过。
- 错误哈希被拒绝，原安装状态保持不变；安装过程中没有执行题库代码，也没有自动授予代码信任。

首发环境 knowledge-release 已要求仓库所有者审核。本次只根据所有者在对话中的明确批准放行 knowledge-v1.0.0；以后版本仍须重新确认。
