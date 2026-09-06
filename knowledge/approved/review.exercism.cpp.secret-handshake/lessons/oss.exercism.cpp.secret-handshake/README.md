# 解码握手信号

> 未审核的导入草稿，不是已发布课程。

## 学习目标

把整数中的标志位转换为有序动作列表。

知识点：位运算、容器。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Introduction

You are starting a secret coding club with some friends and friends-of-friends.
Not everyone knows each other, so you and your friends have decided to create a secret handshake that you can use to recognize that someone is a member.
You don't want anyone who isn't in the know to be able to crack the code.

You've designed the code so that one person says a number between 1 and 31, and the other person turns it into a series of actions.


# Instructions

Your task is to convert a number between 1 and 31 to a sequence of actions in the secret handshake.

The sequence of actions is chosen by looking at the rightmost five digits of the number once it's been converted to binary.
Start at the right-most digit and move left.

The actions for each number place are:

```plaintext
00001 = wink
00010 = double blink
00100 = close your eyes
01000 = jump
10000 = Reverse the order of the operations in the secret handshake.
```

Let's use the number `9` as an example:

- 9 in binary is `1001`.
- The digit that is farthest to the right is 1, so the first action is `wink`.
- Going left, the next digit is 0, so there is no double-blink.
- Going left again, the next digit is 0, so you leave your eyes open.
- Going left again, the next digit is 1, so you jump.

That was the last digit, so the final code is:

```plaintext
wink, jump
```

Given the number 26, which is `11010` in binary, we get the following actions:

- double blink
- jump
- reverse actions

The secret handshake for 26 is therefore:

```plaintext
jump, double blink
```

~~~~exercism/note
If you aren't sure what binary is or how it works, check out [this binary tutorial][intro-to-binary].

[intro-to-binary]: https://medium.com/basecs/bits-bytes-building-with-binary-13cb4289aafa
~~~~


## 来源

https://github.com/exercism/cpp/tree/413b80a9b94089e4588c50500b8553a59c48cda8/exercises/practice/secret-handshake/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
