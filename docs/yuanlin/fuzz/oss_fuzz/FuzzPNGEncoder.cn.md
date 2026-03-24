# FuzzPNGEncoder (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzPNGEncoder.cpp

## 概述

`FuzzPNGEncoder.cpp` 测试 Skia 的传统 PNG 编码器实现。与 `FuzzPNGRustEncoder` 不同,此 fuzzer 测试基于 libpng 的 C 实现。通过随机图像数据验证编码器的健壮性和输出正确性。

## 架构位置

```
OSS-Fuzz → LLVMFuzzerTestOneInput → fuzz_PNGEncoder → libpng 编码器
```

## 主要类与结构体

**LLVMFuzzerTestOneInput**: 最大输入 262150 字节,测试 PNG 编码流程。

**fuzz_PNGEncoder** (外部定义): 生成随机图像并编码为 PNG 格式。

## 内部实现细节

测试包括:
- 不同色彩类型(灰度、RGB、RGBA)
- 位深度变化(1/2/4/8/16 位)
- 压缩级别(0-9)
- 滤波器类型
- interlacing

## 依赖关系

- `libpng`: PNG 参考实现库
- `src/encode/SkPngEncoder.h`: Skia PNG 编码器接口

## 设计模式与设计决策

通过 fuzzing 发现 libpng 和 Skia 封装层的边界情况问题。

## 性能考量

PNG 编码的计算成本与图像大小和压缩级别成正比。

## 相关文件

- `src/encode/SkPngEncoder.cpp`: PNG 编码器实现
- `fuzz/FuzzEncoders.cpp`: 统一编码器 fuzzer
- `third_party/libpng/`: libpng 库

该 fuzzer 是最早的编码器测试之一(2018年),持续验证 PNG 编码的可靠性。
