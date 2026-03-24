# FuzzPNGRustEncoder (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzPNGRustEncoder.cpp

## 概述

`FuzzPNGRustEncoder.cpp` 是用于测试 Skia 的 Rust 实现 PNG 编码器的 OSS-Fuzz 适配器。该 fuzzer 通过随机图像数据测试 PNG 编码的鲁棒性,重点关注 Rust 编写的编码器实现,以发现潜在的内存安全问题、panic 或编码错误。

## 架构位置

```
OSS-Fuzz → LLVMFuzzerTestOneInput → fuzz_PNGRustEncoder → Rust PNG 编码器
```

## 主要类与结构体

### LLVMFuzzerTestOneInput

```cpp
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
```

**输入限制**: 最大 262150 字节(约 256 KB)
**功能**: 将模糊数据传递给 PNG Rust 编码器测试逻辑

## 公共 API 函数

**fuzz_PNGRustEncoder** (外部定义):
- 解析图像数据
- 调用 Rust PNG 编码器
- 验证输出有效性

## 内部实现细节

### 输入大小选择

262150 字节足以编码:
- 512x512 RGBA 图像
- 或更大的低色深图像
- 同时限制内存使用

### Rust 安全边界

测试 Rust 编码器的:
- FFI 边界安全性
- 内存所有权正确性
- Panic 处理

## 依赖关系

- Rust PNG 编码器实现
- `fuzz/Fuzz.h`: Fuzzing 框架
- LibFuzzer: 模糊测试引擎

## 设计模式与设计决策

### 语言边界测试

重点测试 C++/Rust FFI 边界:
- 指针有效性
- 生命周期管理
- 错误传播

## 性能考量

- **输入限制**: 防止过大输入导致超时
- **编码复杂度**: PNG 编码的计算成本
- **内存分配**: Rust 侧的内存管理

## 相关文件

- `src/encode/SkPngRustEncoder.cpp`: Rust 编码器 FFI 绑定
- `fuzz/FuzzEncoders.cpp`: 其他编码器 fuzzer
- OSS-Fuzz 基础设施: 持续集成执行

该 fuzzer 自 2025 年添加,专注于验证 Skia 新引入的 Rust PNG 编码器的安全性和正确性。
