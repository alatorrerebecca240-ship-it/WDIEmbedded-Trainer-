# 三路传感器估算赛道位置

实现 `line_position_three(left, center, right)`，使用权重 `-1000、0、1000` 计算整数加权平均：

```text
((-1000 × left) + (0 × center) + (1000 × right)) / (left + center + right)
```

返回值偏负表示赛道更靠左，偏正表示更靠右。三个读数全为 0 时返回 0。整数除法向零截断。
