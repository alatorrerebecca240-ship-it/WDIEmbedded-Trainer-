# 拼接问候语

> 未审核的导入草稿，不是已发布课程。

## 学习目标

处理默认名字并拼接完整的输出字符串。

知识点：字符串、指针。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Introduction

In some English accents, when you say "two for" quickly, it sounds like "two fer".
Two-for-one is a way of saying that if you buy one, you also get one for free.
So the phrase "two-fer" often implies a two-for-one offer.

Imagine a bakery that has a holiday offer where you can buy two cookies for the price of one ("two-fer one!").
You take the offer and (very generously) decide to give the extra cookie to someone else in the queue.


# Instructions

Your task is to determine what you will say as you give away the extra cookie.

If you know the person's name (e.g. if they're named Do-yun), then you will say:

```text
One for Do-yun, one for me.
```

If you don't know the person's name, you will say _you_ instead.

```text
One for you, one for me.
```

Here are some examples:

| Name   | Dialogue                    |
| :----- | :-------------------------- |
| Alice  | One for Alice, one for me.  |
| Bohdan | One for Bohdan, one for me. |
|        | One for you, one for me.    |
| Zaphod | One for Zaphod, one for me. |


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/two-fer/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
