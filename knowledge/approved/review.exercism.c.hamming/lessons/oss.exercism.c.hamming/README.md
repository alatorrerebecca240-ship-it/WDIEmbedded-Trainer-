# DNA 差异计数

> 未审核的导入草稿，不是已发布课程。

## 学习目标

逐字符比较等长序列并统计不同位置。

知识点：字符串、循环。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Introduction

Your body is made up of cells that contain DNA.
Those cells regularly wear out and need replacing, which they achieve by dividing into daughter cells.
In fact, the average human body experiences about 10 quadrillion cell divisions in a lifetime!

When cells divide, their DNA replicates too.
Sometimes during this process mistakes happen and single pieces of DNA get encoded with the incorrect information.
If we compare two strands of DNA and count the differences between them, we can see how many mistakes occurred.
This is known as the "Hamming distance".

The Hamming distance is useful in many areas of science, not just biology, so it's a nice phrase to be familiar with :)


# Instructions

Calculate the Hamming distance between two DNA strands.

We read DNA using the letters C, A, G and T.
Two strands might look like this:

    GAGCCTACTAACGGGAT
    CATCGTAATGACGGCCT
    ^ ^ ^  ^ ^    ^^

They have 7 differences, and therefore the Hamming distance is 7.

## Implementation notes

The Hamming distance is only defined for sequences of equal length, so an attempt to calculate it between sequences of different lengths should not work.


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/hamming/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
