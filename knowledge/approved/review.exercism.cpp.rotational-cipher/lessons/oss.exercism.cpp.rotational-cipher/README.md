# 字母轮转加密

> 未审核的导入草稿，不是已发布课程。

## 学习目标

在保留大小写和非字母字符的前提下轮转字母。

知识点：字符、取模运算。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Instructions

Create an implementation of the rotational cipher, also sometimes called the Caesar cipher.

The Caesar cipher is a simple shift cipher that relies on transposing all the letters in the alphabet using an integer key between `0` and `26`.
Using a key of `0` or `26` will always yield the same output due to modular arithmetic.
The letter is shifted for as many values as the value of the key.

The general notation for rotational ciphers is `ROT + <key>`.
The most commonly used rotational cipher is `ROT13`.

A `ROT13` on the Latin alphabet would be as follows:

```text
Plain:  abcdefghijklmnopqrstuvwxyz
Cipher: nopqrstuvwxyzabcdefghijklm
```

It is stronger than the Atbash cipher because it has 27 possible keys, and 25 usable keys.

Ciphertext is written out in the same formatting as the input including spaces and punctuation.

## Examples

- ROT5 `omg` gives `trl`
- ROT0 `c` gives `c`
- ROT26 `Cool` gives `Cool`
- ROT13 `The quick brown fox jumps over the lazy dog.` gives `Gur dhvpx oebja sbk whzcf bire gur ynml qbt.`
- ROT13 `Gur dhvpx oebja sbk whzcf bire gur ynml qbt.` gives `The quick brown fox jumps over the lazy dog.`


## 来源

https://github.com/exercism/cpp/tree/413b80a9b94089e4588c50500b8553a59c48cda8/exercises/practice/rotational-cipher/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
