# 三环电阻读数

> 未审核的导入草稿，不是已发布课程。

## 学习目标

组合有效数字和倍率，返回电阻阻值信息。

知识点：结构体、枚举。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Instructions

If you want to build something using a Raspberry Pi, you'll probably use _resistors_.
For this exercise, you need to know only three things about them:

- Each resistor has a resistance value.
- Resistors are small - so small in fact that if you printed the resistance value on them, it would be hard to read.
  To get around this problem, manufacturers print color-coded bands onto the resistors to denote their resistance values.
- Each band acts as a digit of a number.
  For example, if they printed a brown band (value 1) followed by a green band (value 5), it would translate to the number 15.
  In this exercise, you are going to create a helpful program so that you don't have to remember the values of the bands.
  The program will take 3 colors as input, and outputs the correct value, in ohms.
  The color bands are encoded as follows:

- black: 0
- brown: 1
- red: 2
- orange: 3
- yellow: 4
- green: 5
- blue: 6
- violet: 7
- grey: 8
- white: 9

In Resistor Color Duo you decoded the first two colors.
For instance: orange-orange got the main value `33`.
The third color stands for how many zeros need to be added to the main value.
The main value plus the zeros gives us a value in ohms.
For the exercise it doesn't matter what ohms really are.
For example:

- orange-orange-black would be 33 and no zeros, which becomes 33 ohms.
- orange-orange-red would be 33 and 2 zeros, which becomes 3300 ohms.
- orange-orange-orange would be 33 and 3 zeros, which becomes 33000 ohms.

(If Math is your thing, you may want to think of the zeros as exponents of 10.
If Math is not your thing, go with the zeros.
It really is the same thing, just in plain English instead of Math lingo.)

This exercise is about translating the colors into a label:

> "... ohms"

So an input of `"orange", "orange", "black"` should return:

> "33 ohms"

When we get to larger resistors, a [metric prefix][metric-prefix] is used to indicate a larger magnitude of ohms, such as "kiloohms".
That is similar to saying "2 kilometers" instead of "2000 meters", or "2 kilograms" for "2000 grams".

For example, an input of `"orange", "orange", "orange"` should return:

> "33 kiloohms"

[metric-prefix]: https://en.wikipedia.org/wiki/Metric_prefix


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/resistor-color-trio/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
