# 首个知识包发布准备：foundation.core 1.0.0

当前阶段是待审候选，不是正式 Release。首发范围固定为现有 198 道基础/进阶题，不包含 knowledge/drafts 中的第三方导入或批量生成草稿。

## 本次准备内容

- 27 道编程题都有单独的 reference/，保持 starter/ 未完成状态。
- 覆盖 C、C++、嵌入式、智能车、电设、Linux 基础和 ROS 2 基础；模型题不依赖开发板或 ROS 2 运行时。
- 修复六处浮点测试对 NaN 的误接受，补充回调空指针、单元素缓冲区、采样归一化、ADC 舍入、PID 状态和整数边界测试。
- 69 道选择、53 道判断、49 道填空题的既有答案与解析没有在本次改写，仍须人工核对。
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
