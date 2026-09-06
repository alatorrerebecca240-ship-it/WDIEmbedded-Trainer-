# DNA 转录

> 未审核的导入草稿，不是已发布课程。

## 学习目标

按固定碱基对应关系转换字符串。

知识点：字符串、内存管理。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Introduction

You work for a bioengineering company that specializes in developing therapeutic solutions.

Your team has just been given a new project to develop a targeted therapy for a rare type of cancer.

~~~~exercism/note
It's all very complicated, but the basic idea is that sometimes people's bodies produce too much of a given protein.
That can cause all sorts of havoc.

But if you can create a very specific molecule (called a micro-RNA), it can prevent the protein from being produced.

This technique is called [RNA Interference][rnai].

[rnai]: https://admin.acceleratingscience.com/ask-a-scientist/what-is-rnai/
~~~~


# Instructions

Your task is to determine the RNA complement of a given DNA sequence.

Both DNA and RNA strands are a sequence of nucleotides.

The four nucleotides found in DNA are adenine (**A**), cytosine (**C**), guanine (**G**), and thymine (**T**).

The four nucleotides found in RNA are adenine (**A**), cytosine (**C**), guanine (**G**), and uracil (**U**).

Given a DNA strand, its transcribed RNA strand is formed by replacing each nucleotide with its complement:

- `G` -> `C`
- `C` -> `G`
- `T` -> `A`
- `A` -> `U`

~~~~exercism/note
If you want to look at how the inputs and outputs are structured, take a look at the examples in the test suite.
~~~~


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/rna-transcription/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
