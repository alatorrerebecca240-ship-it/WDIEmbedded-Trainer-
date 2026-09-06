# 飞镖计分

> 未审核的导入草稿，不是已发布课程。

## 学习目标

根据点到圆心的距离判断所在计分区域。

知识点：浮点数、条件分支。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Instructions

Calculate the points scored in a single toss of a Darts game.

[Darts][darts] is a game where players throw darts at a [target][darts-target].

In our particular instance of the game, the target rewards 4 different amounts of points, depending on where the dart lands:

![Our dart scoreboard with values from a complete miss to a bullseye](https://assets.exercism.org/images/exercises/darts/darts-scoreboard.svg)

- If the dart lands outside the target, player earns no points (0 points).
- If the dart lands in the outer circle of the target, player earns 1 point.
- If the dart lands in the middle circle of the target, player earns 5 points.
- If the dart lands in the inner circle of the target, player earns 10 points.

The outer circle has a radius of 10 units (this is equivalent to the total radius for the entire target), the middle circle a radius of 5 units, and the inner circle a radius of 1.
Of course, they are all centered at the same point — that is, the circles are [concentric][] defined by the coordinates (0, 0).

Given a point in the target (defined by its [Cartesian coordinates][cartesian-coordinates] `x` and `y`, where `x` and `y` are [real][real-numbers]), calculate the correct score earned by a dart landing at that point.

## Credit

The scoreboard image was created by [habere-et-dispertire][habere-et-dispertire] using [Inkscape][inkscape].

[darts]: https://en.wikipedia.org/wiki/Darts
[darts-target]: https://en.wikipedia.org/wiki/Darts#/media/File:Darts_in_a_dartboard.jpg
[concentric]: https://mathworld.wolfram.com/ConcentricCircles.html
[cartesian-coordinates]: https://www.mathsisfun.com/data/cartesian-coordinates.html
[real-numbers]: https://www.mathsisfun.com/numbers/real-numbers.html
[habere-et-dispertire]: https://exercism.org/profiles/habere-et-dispertire
[inkscape]: https://en.wikipedia.org/wiki/Inkscape


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/darts/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
