# 计算采样信号有效值

实现 `signal_rms`，计算一组浮点采样的均方根值：

```text
RMS = sqrt((x0² + x1² + ... + xn²) / n)
```

## 要求

- 使用 `double` 累加平方和。
- `samples == NULL` 或 `count == 0` 时返回 `0.0`。
- 不修改输入数组。
- 不使用动态内存。

