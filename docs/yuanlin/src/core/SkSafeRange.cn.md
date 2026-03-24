# SkSafeRange

> 源文件: src/core/SkSafeRange.h

## 概述

`SkSafeRange` 是一个轻量级的范围检查工具类,用于在一系列操作中累积检查数值是否在有效范围内。它采用"粘性错误"机制,即一旦任何一次检查失败,对象的错误状态将被记住,后续可通过 `ok()` 方法查询整体操作是否成功。这个类常用于数据反序列化、参数验证等需要多步范围检查的场景。

## 架构位置

`SkSafeRange` 位于 Skia 的 `src/core` 模块,作为基础工具类:

- **基础层**: 提供安全的范围检查原语
- **上层**: 被序列化/反序列化代码、数据验证模块使用
- **相关系统**: 与 `SkReadBuffer`、`SkWriteBuffer` 等 I/O 类协作
- **使用场景**: 字体数据解析、图像解码、网络数据处理等

## 主要类与结构体

### SkSafeRange

| 属性 | 说明 |
|------|------|
| **继承关系** | 无继承关系,独立工具类 |
| **关键成员变量** | `fOK`: 布尔标志,初始为 true,任何检查失败后变为 false |

轻量级范围检查器,仅占用 1 字节内存。

## 公共 API 函数

### 状态查询

```cpp
// 显式转换为 bool(允许在条件表达式中使用)
explicit operator bool() const { return fOK; }

// 检查是否所有操作都成功
bool ok() const { return fOK; }
```

### 范围检查方法

```cpp
// 检查 value 是否在 [0, max] 范围内
// 成功: 返回原值
// 失败: 返回 0 并设置 ok() 为 false
template <typename T>
T checkLE(uint64_t value, T max);

// 检查 value 是否 >= min
// 成功: 返回原值
// 失败: 返回 min 并设置 ok() 为 false
int checkGE(int value, int min);
```

## 内部实现细节

### checkLE 实现

模板方法 `checkLE` 的实现逻辑:

1. **断言检查**: 确保 `max >= 0`(通过 `SkASSERT`)
2. **范围判断**: 比较 `value` 和 `max`(均转换为 `uint64_t` 避免有符号溢出)
3. **失败处理**: 如果 `value > max`,设置 `fOK = false` 并将 `value` 置为 0
4. **类型转换**: 将结果转换回模板类型 `T` 并返回

设计要点:
- 使用 `uint64_t` 避免有符号整数比较的陷阱
- 失败时返回安全的默认值(0)而非随机值
- 断言确保 `max` 非负,防止误用

### checkGE 实现

检查下界的方法实现:

1. **范围判断**: 比较 `value` 和 `min`
2. **失败处理**: 如果 `value < min`,设置 `fOK = false` 并将 `value` 调整为 `min`
3. **返回修正值**: 无论成功与否,返回确保在范围内的值

设计要点:
- 失败时返回边界值而非任意值
- 允许后续代码继续执行(使用安全的替代值)

### 粘性错误机制

`fOK` 标志的特性:
- **初始状态**: 构造时为 `true`
- **单向转换**: 一旦设为 `false`,无法恢复为 `true`
- **累积语义**: 多次检查的"逻辑与"关系
- **最终判定**: 在操作序列结束时调用 `ok()` 一次性判断整体成功与否

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkTypes.h | 基础类型和宏定义 |
| &lt;cstdint&gt; | 标准整数类型(uint64_t) |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| SkReadBuffer | 反序列化时的范围验证 |
| SkWriteBuffer | 序列化参数检查 |
| 字体解析器 | 字体表数据验证 |
| 图像解码器 | 图像头信息验证 |
| SkPath 构建 | 路径操作参数验证 |

## 设计模式与设计决策

### 防御性编程

返回安全的默认值而非抛出异常:
- 避免异常处理开销(C++ 异常在 Skia 中通常禁用)
- 允许调用者选择错误处理时机(通过 `ok()` 查询)
- 防止使用未初始化或危险的值

### 粘性错误模式

累积错误状态而非即时失败:
- 简化多步验证的错误处理逻辑
- 避免在每次检查后都写 if-else
- 支持一次性判断整个操作序列的有效性

### 模板泛型设计

`checkLE` 使用模板支持多种返回类型:
- 调用者可直接得到期望类型的值
- 避免显式类型转换
- 编译器可优化掉类型转换开销

### 显式 bool 转换

提供 `explicit operator bool()`:
- 允许在条件表达式中使用: `if (range) { ... }`
- `explicit` 防止意外的隐式转换
- 提高代码可读性

## 性能考量

### 零开销抽象

`SkSafeRange` 设计为零开销:
- 仅包含单个 `bool` 成员(1 字节)
- 所有方法均内联(在头文件中定义)
- 编译器可完全优化掉函数调用

### 避免异常处理

不使用 C++ 异常机制:
- 异常处理有显著性能开销
- Skia 在性能关键路径上禁用异常
- 错误标志检查可被编译器优化(分支预测)

### 分支预测友好

错误路径设计为"不太可能"分支:
- 正常情况下 `fOK` 保持 true
- CPU 分支预测器可优化热路径
- 错误处理不影响正常执行性能

### 早期验证

在数据处理早期使用 `SkSafeRange`:
- 避免后续使用无效数据导致更复杂的错误
- 将错误限制在输入验证层
- 减少下游代码的边界检查需求

## 相关文件

| 文件 | 关系 |
|------|------|
| src/core/SkReadBuffer.h/cpp | 使用 SkSafeRange 验证反序列化数据 |
| src/core/SkWriteBuffer.h/cpp | 序列化参数范围检查 |
| src/core/SkPath.cpp | 路径操作参数验证 |
| src/ports/SkFontHost_*.cpp | 字体数据解析验证 |
| src/codec/SkCodec*.cpp | 图像解码器数据验证 |

## 使用示例

```cpp
// 典型使用场景: 验证从网络接收的数据
SkSafeRange range;

uint32_t width = range.checkLE(receivedWidth, MAX_IMAGE_WIDTH);
uint32_t height = range.checkLE(receivedHeight, MAX_IMAGE_HEIGHT);
int depth = range.checkGE(receivedDepth, MIN_DEPTH);

if (!range.ok()) {
    // 某个参数超出范围,拒绝处理
    return nullptr;
}

// 所有参数有效,继续处理
return processImage(width, height, depth);
```

优势:
- 无需为每个检查写 if 语句
- 一次性判断所有参数的有效性
- 失败时使用安全的边界值
