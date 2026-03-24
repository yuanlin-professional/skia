# FuzzJSON (OSS-Fuzz)

> 源文件: fuzz/oss_fuzz/FuzzJSON.cpp

## 概述

`FuzzJSON.cpp` 测试 Skia 的 JSON 解析和序列化功能,使用 `skjson` 模块处理任意 JSON 数据。该 fuzzer 通过随机 JSON 输入发现解析器的潜在崩溃、内存错误或格式化问题。

## 架构位置

测试 `modules/jsonreader/SkJSONReader` 中的 JSON DOM 解析器。

## 主要类与结构体

### FuzzJSON 函数

```cpp
void FuzzJSON(const uint8_t *data, size_t size)
```

执行完整的 JSON 往返测试:
1. 解析输入为 JSON DOM: `skjson::DOM dom(data, size)`
2. 将 DOM 写回流: `dom.write(&wstream)`

### LLVMFuzzerTestOneInput

LibFuzzer 入口,无大小限制,接受任意 JSON 输入。

## 内部实现细节

测试覆盖:
- **解析**: 处理格式错误的 JSON
- **DOM 构建**: 内存管理和树结构
- **序列化**: JSON 生成和格式化
- **边界情况**: 深度嵌套、巨大数字、Unicode 处理

## 依赖关系

- `include/core/SkStream.h`: 流 I/O
- `modules/jsonreader/SkJSONReader.h`: JSON 解析器

## 设计模式与设计决策

**往返测试**: 解析后立即序列化,验证往返一致性。

## 性能考量

- **无大小限制**: 可能处理超大 JSON
- **嵌套深度**: 防止栈溢出
- **内存分配**: 大 JSON 对象的内存管理

## 相关文件

- `modules/jsonreader/SkJSONReader.cpp`: JSON 解析实现
- `modules/skottie/`: 使用 JSON 的动画库

该 fuzzer 自 2018 年运行,显著提高了 Skia JSON 处理的稳定性。
