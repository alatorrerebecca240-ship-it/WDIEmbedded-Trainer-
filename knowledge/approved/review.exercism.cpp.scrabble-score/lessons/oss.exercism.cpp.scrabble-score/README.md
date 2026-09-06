# 计算单词分数

> 未审核的导入草稿，不是已发布课程。

## 学习目标

按字母分值表累计单词的总分。

知识点：字符串、容器。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Introduction

[Scrabble][wikipedia] is a word game where players place letter tiles on a board to form words.
Each letter has a value.
A word's score is the sum of its letters' values.

[wikipedia]: https://en.wikipedia.org/wiki/Scrabble


# Instructions

Your task is to compute a word's Scrabble score by summing the values of its letters.

The letters are valued as follows:

| Letter                       | Value |
| ---------------------------- | ----- |
| A, E, I, O, U, L, N, R, S, T | 1     |
| D, G                         | 2     |
| B, C, M, P                   | 3     |
| F, H, V, W, Y                | 4     |
| K                            | 5     |
| J, X                         | 8     |
| Q, Z                         | 10    |

For example, the word "cabbage" is worth 14 points:

- 3 points for C
- 1 point for A
- 3 points for B
- 3 points for B
- 1 point for A
- 2 points for G
- 1 point for E


## 来源

https://github.com/exercism/cpp/tree/413b80a9b94089e4588c50500b8553a59c48cda8/exercises/practice/scrabble-score/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
