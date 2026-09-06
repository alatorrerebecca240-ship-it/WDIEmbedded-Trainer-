# 考拉兹步数

> 未审核的导入草稿，不是已发布课程。

## 学习目标

按奇偶规则迭代，统计到达 1 的步数。

知识点：循环、条件分支。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Introduction

One evening, you stumbled upon an old notebook filled with cryptic scribbles, as though someone had been obsessively chasing an idea.
On one page, a single question stood out: **Can every number find its way to 1?**
It was tied to something called the **Collatz Conjecture**, a puzzle that has baffled thinkers for decades.

The rules were deceptively simple.
Pick any positive integer.

- If it's even, divide it by 2.
- If it's odd, multiply it by 3 and add 1.

Then, repeat these steps with the result, continuing indefinitely.

Curious, you picked number 12 to test and began the journey:

12 ➜ 6 ➜ 3 ➜ 10 ➜ 5 ➜ 16 ➜ 8 ➜ 4 ➜ 2 ➜ 1

Counting from the second number (6), it took 9 steps to reach 1, and each time the rules repeated, the number kept changing.
At first, the sequence seemed unpredictable — jumping up, down, and all over.
Yet, the conjecture claims that no matter the starting number, we'll always end at 1.

It was fascinating, but also puzzling.
Why does this always seem to work?
Could there be a number where the process breaks down, looping forever or escaping into infinity?
The notebook suggested solving this could reveal something profound — and with it, fame, [fortune][collatz-prize], and a place in history awaits whoever could unlock its secrets.

[collatz-prize]: https://mathprize.net/posts/collatz-conjecture/


# Instructions

Given a positive integer, return the number of steps it takes to reach 1 according to the rules of the Collatz Conjecture.


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/collatz-conjecture/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
