# SkTo

> 源文件: `include/private/base/SkTo.h`

## 概述

SkTo 提供了一套类型安全的数值转换模板函数，用于在不同整数类型之间进行安全转换。它利用 SkTFitsIn 在运行时验证转换是否会导致数据丢失，并在调试模式下通过断言捕获错误转换，是 Skia 中防止整数溢出和截断的核心工具。

## 架构位置

本模块位于 Skia 的私有基础设施层，属于类型安全工具集。它被 Skia 的所有需要进行整数类型转换的代码广泛使用，提供了比 C++ 标准 static_cast 更安全的转换机制。

## 主要函数

### 核心模板

#### `SkTo<D, S>()`

```cpp
template <typename D, typename S> constexpr D SkTo(S s)
```

- **功能**: 将类型 S 的值转换为类型 D，并在调试模式下验证转换的有效性
- **模板参数**:
  - `D`: 目标类型
  - `S`: 源类型
- **参数**: `s` - 待转换的值
- **返回值**: 转换后的值（类型为 D）
- **实现**:
  ```cpp
  return SkASSERT(SkTFitsIn<D>(s)), static_cast<D>(s);
  ```
- **行为**:
  - 调试模式：如果转换会导致数据丢失，触发断言
  - 发布模式：直接执行 static_cast（假设转换有效）
- **constexpr**: 可用于编译期常量表达式

### 专用转换函数

#### `SkToS8()`

```cpp
template <typename S> constexpr int8_t SkToS8(S x)
```

- **功能**: 转换为 int8_t（-128 到 127）
- **用途**: 转换为有符号 8 位整数

#### `SkToU8()`

```cpp
template <typename S> constexpr uint8_t SkToU8(S x)
```

- **功能**: 转换为 uint8_t（0 到 255）
- **用途**: 常用于颜色分量转换

#### `SkToS16()`

```cpp
template <typename S> constexpr int16_t SkToS16(S x)
```

- **功能**: 转换为 int16_t（-32768 到 32767）
- **用途**: 转换为有符号 16 位整数

#### `SkToU16()`

```cpp
template <typename S> constexpr uint16_t SkToU16(S x)
```

- **功能**: 转换为 uint16_t（0 到 65535）
- **用途**: 常用于 16 位颜色格式

#### `SkToS32()`

```cpp
template <typename S> constexpr int32_t SkToS32(S x)
```

- **功能**: 转换为 int32_t（-2^31 到 2^31-1）
- **用途**: 转换为有符号 32 位整数

#### `SkToU32()`

```cpp
template <typename S> constexpr uint32_t SkToU32(S x)
```

- **功能**: 转换为 uint32_t（0 到 2^32-1）
- **用途**: 常用于颜色打包、尺寸计算

#### `SkToS64()`

```cpp
template <typename S> constexpr int64_t SkToS64(S x)
```

- **功能**: 转换为 int64_t
- **用途**: 转换为有符号 64 位整数

#### `SkToU64()`

```cpp
template <typename S> constexpr uint64_t SkToU64(S x)
```

- **功能**: 转换为 uint64_t
- **用途**: 转换为无符号 64 位整数

#### `SkToInt()`

```cpp
template <typename S> constexpr int SkToInt(S x)
```

- **功能**: 转换为 int（通常是 32 位）
- **用途**: 最常用的转换函数，广泛用于数组索引、循环计数等

#### `SkToUInt()`

```cpp
template <typename S> constexpr unsigned SkToUInt(S x)
```

- **功能**: 转换为 unsigned int
- **用途**: 转换为无符号整数

#### `SkToSizeT()`

```cpp
template <typename S> constexpr size_t SkToSizeT(S x)
```

- **功能**: 转换为 size_t（平台相关大小）
- **用途**: 用于内存大小、数组长度等

### 布尔转换

#### `SkToBool()`

```cpp
template <typename T> static constexpr bool SkToBool(const T& x)
```

- **功能**: 将任意类型转换为布尔值
- **实现**: `return (bool)x;`
- **返回值**:
  - `x` 为零值时返回 false
  - `x` 为非零值时返回 true
- **用途**: 显式地将整数、指针等转换为布尔值

## 内部实现细节

### SkTFitsIn 验证

`SkTo` 依赖 `SkTFitsIn<D>(s)` 进行范围检查：

```cpp
template <typename D, typename S> constexpr D SkTo(S s) {
    return SkASSERT(SkTFitsIn<D>(s)),  // 验证转换有效性
           static_cast<D>(s);           // 执行转换
}
```

`SkTFitsIn` 在编译期或运行期检查：
- 源值是否在目标类型的表示范围内
- 符号转换是否会导致错误（如负数转无符号数）
- 浮点数转整数是否会溢出

### 逗号运算符技巧

使用逗号运算符将断言和转换组合在一起：
- 左侧：`SkASSERT(SkTFitsIn<D>(s))` 验证有效性
- 右侧：`static_cast<D>(s)` 执行转换
- 整个表达式的值为右侧的结果

这种写法保持了 constexpr 特性，因为在编译期 SkASSERT 会被忽略。

### 调试 vs. 发布模式

- **调试模式**: `SkASSERT` 展开为实际的断言检查，无效转换会触发程序终止
- **发布模式**: `SkASSERT` 展开为空，直接执行 static_cast，零开销

### constexpr 支持

所有函数都是 constexpr，允许：
- 编译期常量转换
- 在 constexpr 上下文中使用
- 编译器优化

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkAssert.h | 断言宏 SkASSERT |
| SkTFitsIn.h | 范围检查模板 |
| &lt;cstddef&gt; | size_t 定义 |
| &lt;cstdint&gt; | 固定宽度整数类型 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| SkRect.h | 坐标转换 |
| SkBitmap.h | 尺寸转换 |
| SkPath.h | 点计数转换 |
| SkCanvas.h | 参数转换 |
| 几乎所有 Skia 模块 | 广泛使用 |

## 设计模式与设计决策

### 显式转换哲学

Skia 禁止隐式整数类型转换，强制使用 SkTo 系列函数，这带来：
- 代码意图更清晰
- 转换点一目了然
- 容易审查和调试

### 零开销抽象

在发布模式下，SkTo 函数编译为与 static_cast 完全相同的代码，没有额外开销。

### 防御性编程

在开发阶段通过断言捕获错误转换，避免了难以调试的整数溢出 bug。

### 模板特化

为常用类型提供命名函数（如 SkToInt），提高代码可读性：

```cpp
// 清晰的意图
int index = SkToInt(size);

// vs. 需要思考的代码
int index = SkTo<int>(size);
```

## 性能考量

### 零运行时开销

发布版本中，SkTo 函数完全内联为 static_cast，没有函数调用开销。

### 编译期优化

constexpr 特性允许编译器在编译期完成转换和检查。

### 调试开销

调试模式下的范围检查有轻微开销，但这是开发期间可接受的代价。

### 内联友好

所有函数都定义在头文件中，编译器可以轻松内联。

## 常见使用场景

### 尺寸转换

```cpp
size_t count = ...;
int iCount = SkToInt(count);  // 确保 count 适合 int
```

### 坐标转换

```cpp
float x = 123.5f;
int ix = SkToInt(x);  // 转换为整数坐标
```

### 颜色分量

```cpp
float alpha = 0.5f;
uint8_t a = SkToU8(alpha * 255);  // 转换为 8 位颜色
```

### 循环索引

```cpp
for (int i = 0; i < SkToInt(array.size()); ++i) {
    // 安全地将 size_t 转换为 int
}
```

## 典型错误案例

### 负数转无符号数

```cpp
int value = -1;
uint32_t u = SkToU32(value);  // 调试模式：断言失败
```

### 值超出范围

```cpp
int64_t large = 0x1FFFFFFFFLL;
int32_t i = SkToS32(large);  // 调试模式：断言失败
```

### 浮点数溢出

```cpp
float huge = 1e20f;
int i = SkToInt(huge);  // 调试模式：断言失败
```

## 最佳实践

### 尽早转换

在数据进入系统时尽早转换为合适的类型，而不是在使用时临时转换。

### 选择合适的类型

优先使用语义明确的固定宽度类型（如 int32_t）而非平台相关的类型（如 int）。

### 审查转换点

代码审查时特别关注 SkTo 调用，确保转换有意义。

### 避免链式转换

```cpp
// 不好
int value = SkToInt(SkToU32(SkToS64(x)));

// 好
int64_t temp = SkToS64(x);
// ... 验证 temp 的范围 ...
int value = SkToInt(temp);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/base/SkTFitsIn.h` | 范围检查实现 |
| `include/private/base/SkAssert.h` | 断言宏定义 |
| `include/core/SkScalar.h` | 标量类型转换 |
| `include/core/SkTypes.h` | 基本类型定义 |
