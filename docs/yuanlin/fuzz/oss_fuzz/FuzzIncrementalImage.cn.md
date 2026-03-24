# FuzzIncrementalImage (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzIncrementalImage.cpp

## 概述

测试图像的增量解码功能,模拟网络传输场景中数据逐步到达的情况。增量解码允许在完整数据到达前开始渲染,提升用户体验。

## 架构位置

测试 `include/codec/SkCodec.h` 的增量解码 API。

## 主要类与结构体

### FuzzIncrementalImageDecode 函数

```cpp
bool FuzzIncrementalImageDecode(const uint8_t *data, size_t size)
```

流程:
1. 创建编解码器: `SkCodec::MakeFromStream(...)`
2. 分配位图
3. 开始增量解码: `startIncrementalDecode(...)`
4. 执行增量解码: `incrementalDecode(&rowsDecoded)`
5. 处理不完整输入:
   - `kIncompleteInput`: 数据不足
   - `kErrorInInput`: 数据错误
   - 填充未解码行为零

### LLVMFuzzerTestOneInput

最大 10240 字节,模拟部分图像数据。

## 内部实现细节

### 增量解码状态

- **kSuccess**: 完全解码
- **kIncompleteInput**: 需要更多数据
- **kErrorInInput**: 遇到错误但可部分显示

### 行追踪

`rowsDecoded` 参数:
- 记录已解码的行数
- 用于填充剩余行
- 支持渐进式渲染

### 编解码器支持

支持增量解码的格式:
- PNG (interlaced)
- JPEG (progressive)
- GIF
- WebP

## 依赖关系

- `include/codec/SkCodec.h`: 编解码器接口
- `src/codec/`: 各格式的编解码器实现

## 设计模式与设计决策

**错误恢复**: 即使数据不完整或有错误,也尝试显示部分图像。

## 性能考量

增量解码需要维护解码状态,可能比一次性解码稍慢。

## 相关文件

- `src/codec/SkPngCodec.cpp`: PNG 增量解码
- `tests/CodecTest.cpp`: 编解码器测试

该 fuzzer 确保增量解码的鲁棒性,对 web 浏览器的图像加载体验至关重要。
