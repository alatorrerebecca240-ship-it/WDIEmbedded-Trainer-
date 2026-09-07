# 查询幼儿园种植分工

读取两行植物编码，找出指定孩子负责的四盆植物。

知识点：枚举、字符串视图、数组、索引计算

## 题目要求

班级按姓名字母顺序为以下 12 位孩子分配花盆：

`Alice, Bob, Charlie, David, Eve, Fred, Ginny, Harriet, Ileana, Joseph, Kincaid, Larry`

花盆排成两行。每个孩子负责每行相邻的两盆，共四盆。Alice 负责每行最左边两盆，Bob 负责接下来的两盆，依此类推。

| 编码 | 植物 | 返回枚举 |
| --- | --- | --- |
| G | 草 | `Plants::grass` |
| C | 三叶草 | `Plants::clover` |
| R | 萝卜 | `Plants::radishes` |
| V | 紫罗兰 | `Plants::violets` |

实现 `kindergarten_garden::plants(diagram, student)`，返回 `std::array<Plants, 4>`。输入两行之间以换行符分隔。返回顺序为第一行的两盆（从左到右），再第二行的两盆。

## 示例

```text
VRCGVVRVCGGCCGVRGCVCGCGV
VRCCCGCRRGVCGCRVVCVGCGCV
```

Alice 的结果是紫罗兰、萝卜、紫罗兰、萝卜；Bob 的结果是三叶草、草、三叶草、三叶草。窗口示意文字不是输入的一部分。

## 提示

- 先确定孩子在名单中的序号，再乘以 2 得到每行的起始下标。
- 第二行的起点在换行符之后，不要把换行符当作植物。
- 返回枚举值，不是中文植物名称字符串。
