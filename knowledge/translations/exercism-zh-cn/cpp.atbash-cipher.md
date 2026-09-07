# 字母倒序替换密码

实现 Atbash 字母替换，并处理数字、标点和分组空格。

知识点：字符串、字符映射、循环、格式化

## 题目要求

将英文字母按字母表首尾对应替换：`a` 与 `z`、`b` 与 `y`，依此类推。

```text
原字母：abcdefghijklmnopqrstuvwxyz
替换后：zyxwvutsrqponmlkjihgfedcba
```

实现 `atbash_cipher::encode` 和 `decode`。编码统一使用小写字母，数字保持不变，忽略标点与原来的空白；每五个有效输出字符插入一个分组空格，末尾不要多加空格。数字也计入分组长度。

解码时去掉分组空格，执行相同的字母映射，返回连续文本，不恢复原来的词间空格。此方法仅适合学习，不适合保护实际敏感信息。

## 示例

- 编码 `test` → `gvhg`。
- 编码 `x123 yes` → `c123b vh`。
- 解码 `gvhg` → `test`。
- 解码 `gsvjf rxpyi ldmul cqfnk hlevi gsvoz abwlt` → `thequickbrownfoxjumpsoverthelazydog`。

## 提示

- 先区分字母、数字和应忽略的字符。
- 字母映射可以通过字符相对 `a` 的偏移量计算。
- 分组依据输出的有效字符数量，而不是输入位置。
