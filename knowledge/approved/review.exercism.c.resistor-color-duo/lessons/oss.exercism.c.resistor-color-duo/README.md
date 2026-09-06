# 双环电阻数值

> 未审核的导入草稿，不是已发布课程。

## 学习目标

组合前两个电阻色环表示的数字。

知识点：枚举、数组。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Instructions

If you want to build something using a Raspberry Pi, you'll probably use _resistors_.
For this exercise, you need to know two things about them:

- Each resistor has a resistance value.
- Resistors are small - so small in fact that if you printed the resistance value on them, it would be hard to read.

To get around this problem, manufacturers print color-coded bands onto the resistors to denote their resistance values.
Each band has a position and a numeric value.

The first 2 bands of a resistor have a simple encoding scheme: each color maps to a single number.
For example, if they printed a brown band (value 1) followed by a green band (value 5), it would translate to the number 15.

In this exercise you are going to create a helpful program so that you don't have to remember the values of the bands.
The program will take color names as input and output a two digit number, even if the input is more than two colors!

The band colors are encoded as follows:

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

From the example above:
brown-green should return 15, and
brown-green-violet should return 15 too, ignoring the third color.


## 来源

https://github.com/exercism/c/tree/2e8a0022fd2a611adc08b4d6e70d07b988cc5364/exercises/practice/resistor-color-duo/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
