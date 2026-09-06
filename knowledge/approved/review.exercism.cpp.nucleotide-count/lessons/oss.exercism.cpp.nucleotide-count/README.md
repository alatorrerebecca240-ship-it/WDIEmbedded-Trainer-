# Nucleotide Count

> 未审核的导入草稿，不是已发布课程。

## 学习目标

Given a DNA string, compute how many times each nucleotide occurs in the string.

知识点：parsing、strings。

## 实作要求

保留测试要求的函数接口，在 starter 中完成实现。请先阅读原题的边界约定；本版提供中文学习目标，以下英文原题完整保留，中文题干精校与初始接口补齐仍属于审核工作。

## 上游原题

# Instructions

Each of us inherits from our biological parents a set of chemical instructions known as DNA that influence how our bodies are constructed.
All known life depends on DNA!

> Note: You do not need to understand anything about nucleotides or DNA to complete this exercise.

DNA is a long chain of other chemicals and the most important are the four nucleotides, adenine, cytosine, guanine and thymine.
A single DNA chain can contain billions of these four nucleotides and the order in which they occur is important!
We call the order of these nucleotides in a bit of DNA a "DNA sequence".

We represent a DNA sequence as an ordered collection of these four nucleotides and a common way to do that is with a string of characters such as "ATTACG" for a DNA sequence of 6 nucleotides.
'A' for adenine, 'C' for cytosine, 'G' for guanine, and 'T' for thymine.

Given a string representing a DNA sequence, count how many of each nucleotide is present.
If the string contains characters that aren't A, C, G, or T then it is invalid and you should signal an error.

For example:

```text
"GATTACA" -> 'A': 3, 'C': 1, 'G': 1, 'T': 2
"INVALID" -> error
```


## 来源

https://github.com/exercism/cpp/tree/413b80a9b94089e4588c50500b8553a59c48cda8/exercises/practice/nucleotide-count/

题目和参考实现：Exercism MIT；测试框架保留各自许可。
