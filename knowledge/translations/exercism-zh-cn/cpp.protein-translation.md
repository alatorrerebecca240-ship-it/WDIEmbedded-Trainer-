# 将 RNA 序列翻译为氨基酸

每三个碱基读取一个密码子，将 RNA 转换为有序的氨基酸名称列表。

知识点：字符串切片、映射容器、循环、提前结束

## 题目要求

RNA 中连续三个碱基称为一个密码子。多个氨基酸连接起来可以形成蛋白质。本题只使用下表列出的密码子，不需要掌握完整的生物学规则。

实现 `protein_translation::proteins(std::string rna)`，返回 `std::vector<std::string>`。必须返回表中的英文名称，中文只是帮助理解。

| 密码子 | 氨基酸中文名 | 结果字符串 |
| --- | --- | --- |
| AUG | 甲硫氨酸 | `Methionine` |
| UUU、UUC | 苯丙氨酸 | `Phenylalanine` |
| UUA、UUG | 亮氨酸 | `Leucine` |
| UCU、UCC、UCA、UCG | 丝氨酸 | `Serine` |
| UAU、UAC | 酪氨酸 | `Tyrosine` |
| UGU、UGC | 半胱氨酸 | `Cysteine` |
| UGG | 色氨酸 | `Tryptophan` |
| UAA、UAG、UGA | 停止信号 | 不加入结果，立即结束 |

从字符串开头按三个字符一组处理，保持顺序。遇到任意停止密码子后，忽略其后的整个序列；停止信号本身不属于返回列表。

## 示例

`AUGUUUUCU` 分为 `AUG`、`UUU`、`UCU`，得到 `Methionine`、`Phenylalanine`、`Serine`。

`AUGUUUUCUUAAAUG` 在 `UAA` 处停止，结果与上例相同，末尾的 `AUG` 不再处理。

## 提示

- 每次将读取位置增加 3，而不是增加 1。
- 多个密码子可以对应同一个氨基酸名称。
- 停止信号意味着结束整个循环，不是仅跳过当前这一组。
