# FuzzWEBPEncoder (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzWEBPEncoder.cpp

## 概述

`FuzzWEBPEncoder.cpp` 是用于测试 Skia WEBP 图像编码器的 OSS-Fuzz 适配器。WEBP 是 Google 开发的现代图像格式,支持有损和无损压缩。该 fuzzer 通过随机输入测试编码器的稳定性,特别关注内存安全、编码正确性和边界情况处理。

## 架构位置

```
OSS-Fuzz → LLVMFuzzerTestOneInput → fuzz_WEBPEncoder → libwebp 编码库
```

## 主要类与结构体

### LLVMFuzzerTestOneInput

```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
```

**输入限制**: 最大 262150 字节
**功能**: 测试 WEBP 编码流程的各种参数组合

## 公共 API 函数

**fuzz_WEBPEncoder** (外部定义):
- 解析图像宽高、格式
- 生成随机编码参数(质量、预设等)
- 执行 WEBP 编码
- 验证输出

## 内部实现细节

### WEBP 编码器特性

测试包括:
- **压缩模式**: 有损 vs 无损
- **质量参数**: 0-100 的质量设置
- **预设**: 默认、图片、照片、绘图、图标、文本
- **高级选项**: 多线程、Alpha 压缩等

### libwebp 集成

Skia 使用 Google 的 libwebp 库:
- C 接口绑定
- 内存管理
- 错误处理

## 依赖关系

- `libwebp`: Google WEBP 编码/解码库
- `src/encode/SkWebpEncoder.cpp`: Skia WEBP 编码器封装
- LibFuzzer: 模糊测试引擎

## 设计模式与设计决策

### 多参数空间覆盖

通过随机化以下参数:
- 图像尺寸和色彩空间
- 编码质量和压缩级别
- 特殊编码选项

### 外部库安全

重点测试 libwebp 的:
- 输入验证
- 缓冲区管理
- 错误路径

## 性能考量

- **编码成本**: WEBP 编码计算密集
- **内存峰值**: 高质量编码需要大量内存
- **超时保护**: 复杂图像可能导致超时

## 相关文件

- `src/encode/SkWebpEncoder.h`: WEBP 编码器接口
- `fuzz/FuzzEncoders.cpp`: 统一的编码器 fuzzer
- `third_party/libwebp/`: libwebp 库源码

**典型发现的问题**:
- 整数溢出
- 缓冲区越界
- 除零错误
- 断言失败

该 fuzzer 自 2018 年持续运行,显著提高了 Skia WEBP 编码的可靠性和安全性。
