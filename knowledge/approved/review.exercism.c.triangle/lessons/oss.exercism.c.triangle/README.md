# 判断三角形类别

> 未审核的导入草稿，不是已发布课程。

## 学习目标

先验证边长，再区分等边、等腰和不等边三角形。

知识点：条件分支、浮点数。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Instructions

Determine if a triangle is equilateral, isosceles, or scalene.

An _equilateral_ triangle has all three sides the same length.

An _isosceles_ triangle has at least two sides the same length.
(It is sometimes specified as having exactly two sides the same length, but for the purposes of this exercise we'll say at least two.)

A _scalene_ triangle has all sides of different lengths.

## Note

For a shape to be a triangle at all, all sides have to be of length > 0, and the sum of the lengths of any two sides must be greater than or equal to the length of the third side.

~~~~exercism/note
_Degenerate triangles_ are triangles where the sum of the length of two sides is **equal** to the length of the third side, e.g. `1, 1, 2`.
We opted to not include tests for degenerate triangles in this exercise.
You may handle those situations if you wish to do so, or safely ignore them.
~~~~

In equations:

Let `a`, `b`, and `c` be sides of the triangle.
Then all three of the following expressions must be true:

```text
a + b ≥ c
b + c ≥ a
a + c ≥ b
```

See [Triangle Inequality][triangle-inequality]

[triangle-inequality]: https://en.wikipedia.org/wiki/Triangle_inequality


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/triangle/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
