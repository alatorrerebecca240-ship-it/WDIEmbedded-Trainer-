# 判断公历闰年

> 未审核的导入草稿，不是已发布课程。

## 学习目标

组合整除条件，正确处理世纪年。

知识点：条件分支、逻辑运算。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Introduction

A leap year (in the Gregorian calendar) occurs:

- In every year that is evenly divisible by 4.
- Unless the year is evenly divisible by 100, in which case it's only a leap year if the year is also evenly divisible by 400.

Some examples:

- 1997 was not a leap year as it's not divisible by 4.
- 1900 was not a leap year as it's not divisible by 400.
- 2000 was a leap year!

~~~~exercism/note
For a delightful, four-minute explanation of the whole phenomenon of leap years, check out [this YouTube video](https://www.youtube.com/watch?v=xX96xng7sAE).
~~~~


# Instructions

Your task is to determine whether a given year is a leap year.


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/leap/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
