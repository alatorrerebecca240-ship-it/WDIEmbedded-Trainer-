# Atbash Cipher

> 未审核的导入草稿，不是已发布课程。

## 学习目标

Create an implementation of the Atbash cipher, an ancient encryption system created in the Middle East.

知识点：algorithms、strings。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Instructions

Create an implementation of the Atbash cipher, an ancient encryption system created in the Middle East.

The Atbash cipher is a simple substitution cipher that relies on transposing all the letters in the alphabet such that the resulting alphabet is backwards.
The first letter is replaced with the last letter, the second with the second-last, and so on.

An Atbash cipher for the Latin alphabet would be as follows:

```text
Plain:  abcdefghijklmnopqrstuvwxyz
Cipher: zyxwvutsrqponmlkjihgfedcba
```

It is a very weak cipher because it only has one possible key, and it is a simple mono-alphabetic substitution cipher.
However, this may not have been an issue in the cipher's time.

Ciphertext is written out in groups of fixed length, the traditional group size being 5 letters, leaving numbers unchanged, and punctuation is excluded.
This is to make it harder to guess things based on word boundaries.
All text will be encoded as lowercase letters.

## Examples

- Encoding `test` gives `gvhg`
- Encoding `x123 yes` gives `c123b vh`
- Decoding `gvhg` gives `test`
- Decoding `gsvjf rxpyi ldmul cqfnk hlevi gsvoz abwlt` gives `thequickbrownfoxjumpsoverthelazydog`


## 来源

https://github.com/exercism/cpp/tree/413b80a9b94089e4588c50500b8553a59c48cda8/exercises/practice/atbash-cipher/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
