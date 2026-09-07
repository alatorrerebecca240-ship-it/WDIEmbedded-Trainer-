# 字母轮转加密

将英文字母循环移动指定位置，同时保留大小写和其他字符。

知识点：字符运算、取模运算、字符串、条件分支

## 题目要求

实现 `rotational_cipher::rotate(text, shift_key)`。密钥在 0—26 之间，每个英文字母在自己的大小写字母表中向后移动相应位置，超过 `z` 或 `Z` 后绕回开头。

密钥为 0 或 26 时，文本不变。空格、数字、标点保持原样，不能像另一道 Atbash 题那样删掉标点或插入分组空格。此密码仅用于理解字符映射，不适合实际保密。

## 示例

- ROT5：`omg` → `trl`。
- ROT0：`c` → `c`。
- ROT26：`Cool` → `Cool`。
- ROT13：`The quick brown fox jumps over the lazy dog.` → `Gur dhvpx oebja sbk whzcf bire gur ynml qbt.`。
- 对上述 ROT13 结果再做一次 ROT13，会恢复原文。

## 提示

- 小写字母以 `a` 为基准，大写字母以 `A` 为基准。
- 使用对 26 取模来实现回绕。
- 非英文字母应直接加入结果，不执行偏移计算。
