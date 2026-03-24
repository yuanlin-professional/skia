# SkottieJson - Skottie JSON 值解析工具

> 源文件: [`modules/skottie/src/SkottieJson.h`](../../../modules/skottie/src/SkottieJson.h), [`modules/skottie/src/SkottieJson.cpp`](../../../modules/skottie/src/SkottieJson.cpp)

## 概述

SkottieJson 提供了一组模板化的 JSON 值解析函数，将 skjson::Value 转换为 Skia 的基本类型（SkScalar、bool、int、size_t、SkString、SkV2、SkPoint、VectorValue）。这些函数是 Skottie 动画解析器的基础设施，处理了 Lottie/After Effects JSON 格式的各种特殊情况。

## 架构位置

位于 Skottie 模块的内部实现层，被几乎所有 Skottie 解析代码依赖：

- **上层使用者**: AnimationBuilder、各种图层/效果/变换解析器
- **底层依赖**: skjson（JSON DOM）

## 主要类与结构体

无独立类定义。提供模板函数 `Parse<T>` 和辅助函数 `ParseDefault<T>`。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `Parse<T>(value, result)` | 将 JSON Value 解析为类型 T，成功返回 true |
| `ParseDefault<T>(value, defaultValue)` | 解析 JSON Value，失败时返回默认值 |
| `ParseSlotID(jobj)` | 从 JSON 对象中提取 "sid"（slot ID）字符串 |

### 支持的类型特化

| 类型 | 解析行为 |
|------|----------|
| `SkScalar` | 从 NumberValue 提取，支持单元素数组包装 |
| `bool` | 从 BoolValue 或 NumberValue（非零 = true）提取 |
| `int` | 从 NumberValue 提取，带溢出检查 |
| `size_t` | 从 NumberValue 提取，带溢出检查 |
| `SkString` | 从 StringValue 提取 |
| `SkV2` | 从至少 2 元素的 ArrayValue 提取 x,y |
| `SkPoint` | 从包含 "x","y" 键的 ObjectValue 提取 |
| `VectorValue` | 从 ArrayValue 提取 SkScalar 向量 |

## 内部实现细节

### SkScalar 的数组包装兼容
某些 Lottie 版本将标量值包装为单元素数组（如 `[42]` 而非 `42`）。Parse<SkScalar> 会自动解包这种格式。

### bool 的数字兼容
布尔值可以是实际的 JSON boolean 或 number（非零视为 true），兼容不同导出器的行为。

### 整数溢出保护
ParseIntegral 模板函数在转换前检查 double 值是否在目标类型的范围内，防止未定义行为。

## 依赖关系

- `modules/jsonreader/SkJSONReader.h` - JSON Value 类型
- `modules/skottie/src/SkottieValue.h` - VectorValue 类型定义
- `include/core/SkM44.h` - SkV2 类型
- `include/core/SkPoint.h` - SkPoint 类型

## 设计模式与设计决策

### 模板特化模式
使用 C++ 模板特化为每种类型提供定制的解析逻辑，同时保持统一的调用接口。

### 宽松解析
设计为尽可能容忍 JSON 格式的变体，反映了 Lottie 生态中不同导出器（After Effects、Bodymovin 等）的行为差异。

## 性能考量

- 所有解析都是 O(1) 操作（VectorValue 除外，其为 O(n)）
- 无动态内存分配
- ParseDefault 使用值语义，适合内联优化

## 相关文件

- `modules/jsonreader/SkJSONReader.h` - JSON DOM 和值类型
- `modules/skottie/src/SkottiePriv.h` - 内部 AnimationBuilder
- `modules/skottie/src/SkottieValue.h` - VectorValue 等值类型
