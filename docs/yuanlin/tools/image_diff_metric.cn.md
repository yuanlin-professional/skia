# image_diff_metric - 图像差异度量工具

> 源文件: `tools/image_diff_metric.cpp`

## 概述

`image_diff_metric` 是一个命令行工具,计算两张编码图像之间的差异度量值。输出 0.0 到 1.0 之间的浮点数:0 表示完全相同,1 表示每个像素在每个通道上都达到最大差异。使用 ARGB 颜色空间的曼哈顿距离计算。

## 架构位置

属于 Skia 工具链中的图像比较工具,可用于自动化测试和质量验证。

## 公共 API 函数

- **`main(argc, argv)`**: 读取两张图片,计算并输出差异值

## 内部实现细节

- 使用 SkCodec 解码输入图像(支持 PNG、JPEG 等)
- 强制转换为 N32 (BGRA/RGBA 8888) 像素格式
- 逐像素逐通道计算绝对差异之和
- 归一化: `totalDiffs / (255 * 4 * width * height)`

## 依赖关系

- `include/codec/SkCodec.h` - 图像解码
- `include/core/SkBitmap.h`, `SkData.h`, `SkPixmap.h`

## 设计模式与设计决策

- **简单可靠**: 使用曼哈顿距离而非更复杂的感知度量,便于自动化比较
- **退出码语义**: 0=成功, 1=参数错误, 2=文件错误, 3=尺寸不匹配

## 性能考量

O(width * height) 逐像素扫描,对大图像有一定开销。

## 相关文件

- Gold 图像比较服务(更复杂的图像差异检测)
