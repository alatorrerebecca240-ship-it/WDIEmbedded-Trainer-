# ADC 采样值换算毫伏

实现 `adc_to_millivolts(sample, max_code, reference_mv)`，按比例把 ADC 码值转换成毫伏并四舍五入到最接近的整数：

```text
sample × reference_mv / max_code
```

`max_code == 0` 时返回 0。测试保证 `sample <= max_code` 且参考电压不超过 5000 mV。
