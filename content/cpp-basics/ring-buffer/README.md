# 固定容量环形缓冲区

补全 `ring_buffer.hpp` 中的 `RingBuffer<T, Capacity>`。

## 要求

- 先进先出。
- 容量在编译期确定。
- 不进行动态内存分配。
- 缓冲区已满时 `push` 返回 `false`。
- 缓冲区为空时 `pop` 返回 `std::nullopt`。
- 正确处理读写索引回绕。

完成后运行：

```text
trainer check cpp.container.ring-buffer-01
```

