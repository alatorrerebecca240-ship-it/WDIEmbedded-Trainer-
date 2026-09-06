# 按因数转换文本

> 未审核的导入草稿，不是已发布课程。

## 学习目标

根据能否整除 3、5、7 生成对应文本。

知识点：条件分支、字符串。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Introduction

Raindrops is a slightly more complex version of the FizzBuzz challenge, a classic interview question.


# Instructions

Your task is to convert a number into its corresponding raindrop sounds.

If a given number:

- is divisible by 3, add "Pling" to the result.
- is divisible by 5, add "Plang" to the result.
- is divisible by 7, add "Plong" to the result.
- **is not** divisible by 3, 5, or 7, the result should be the number as a string.

## Examples

- 28 is divisible by 7, but not 3 or 5, so the result would be `"Plong"`.
- 30 is divisible by 3 and 5, but not 7, so the result would be `"PlingPlang"`.
- 34 is not divisible by 3, 5, or 7, so the result would be `"34"`.

~~~~exercism/note
A common way to test if one number is evenly divisible by another is to compare the [remainder][remainder] or [modulus][modulo] to zero.
Most languages provide operators or functions for one (or both) of these.

[remainder]: https://exercism.org/docs/programming/operators/remainder
[modulo]: https://en.wikipedia.org/wiki/Modulo_operation
~~~~


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/raindrops/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
