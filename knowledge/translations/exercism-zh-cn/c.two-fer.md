# 拼接分享饼干的问候语

根据是否提供名字，生成一句固定格式的英文问候语。

知识点：字符串、指针、空指针、格式化输出

## 题目要求

你买到了两块饼干，想把其中一块分享给别人。实现 `void two_fer(char *buffer, const char *name)`，把结果写入调用者提供的 `buffer`。

知道对方名字时，输出 `One for <名字>, one for me.`；没有提供名字时，使用 `you`。测试用空指针表示未提供名字，请区分空指针与空字符串。

| 名字 | 结果字符串 |
| --- | --- |
| Alice | `One for Alice, one for me.` |
| Bohdan | `One for Bohdan, one for me.` |
| 未提供 | `One for you, one for me.` |
| Zaphod | `One for Zaphod, one for me.` |

英文结果是评测接口的一部分，不要翻译成中文，也不要改变大小写、逗号、空格或句号。

## 提示

- 读取 `name` 指向的内容之前，先判断指针是否为空。
- 可以先选定要使用的名字，再统一生成结果。
- 结果必须是以 `\0` 结束的 C 字符串。
