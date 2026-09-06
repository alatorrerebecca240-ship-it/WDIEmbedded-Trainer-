# 开发板配置

本目录保存开发板能力描述和工具链参数，不保存课程逻辑。后续每块板可包含：

```text
board.json
toolchain.cmake
platformio.ini
openocd.cfg
README.md
```

算法和业务模块应依赖 GPIO、ADC、PWM、编码器、时钟等抽象接口，再由本目录中的板级实现连接真实硬件。

