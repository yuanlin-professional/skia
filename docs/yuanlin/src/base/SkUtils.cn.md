# SkUtils

> 源文件
> - src/base/SkUtils.h
> - src/base/SkUtils.cpp

## 概述

SkUtils 是 Skia 图形库中的基础实用工具模块,提供了跨平台的内存操作、类型转换和十六进制数字常量等底层功能。该模块通过模板函数和编译器特定的优化,实现了安全的非对齐内存访问和位转换操作,解决了 SIMD 指令与 x87 FPU 寄存器冲突等特殊平台问题。

## 架构位置

SkUtils 位于 Skia 的 base 层(`src/base`),作为最底层的基础设施模块,为整个 Skia 库提供平台无关的内存操作和数据转换支持。它不依赖于任何其他 Skia 模块,仅依赖 C++ 标准库。

## 主要类与结构体

该模块没有定义类,主要通过命名空间和模板函数实现功能。

### 核心组件

| 组件 | 类型 | 说明 |
|------|------|------|
| `SkHexadecimalDigits` | namespace | 提供十六进制字符映射表 |
| `sk_unaligned_load<T>` | template function | 非对齐内存加载 |
| `sk_unaligned_store<T>` | template function | 非对齐内存存储 |
| `sk_bit_cast<Dst, Src>` | template function | 位级类型转换 |

### SkHexadecimalDigits 命名空间

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `gUpper` | `const char[16]` | 大写十六进制字符 (0-9A-F) |
| `gLower` | `const char[16]` | 小写十六进制字符 (0-9a-f) |

## 公共 API 函数

### sk_unaligned_load

```cpp
template <typename T, typename P>
static SK_ALWAYS_INLINE T SK_FP_SAFE_ABI sk_unaligned_load(const P* ptr)
```

**功能**: 从非对齐内存地址安全加载数据

**参数**:
- `ptr`: 源内存指针,可以是非对齐地址
- `T`: 目标类型,必须是 trivially copyable
- `P`: 指针类型

**返回值**: 加载的 T 类型值

**使用场景**: 从未对齐的内存位置读取 SIMD 向量或其他数据结构

### sk_unaligned_store

```cpp
template <typename T, typename P>
static SK_ALWAYS_INLINE void SK_FP_SAFE_ABI sk_unaligned_store(P* ptr, T val)
```

**功能**: 向非对齐内存地址安全存储数据

**参数**:
- `ptr`: 目标内存指针
- `val`: 要存储的值

### sk_bit_cast

```cpp
template <typename Dst, typename Src>
static SK_ALWAYS_INLINE Dst SK_FP_SAFE_ABI sk_bit_cast(const Src& src)
```

**功能**: 执行位级类型转换,类似于 C++20 的 `std::bit_cast`

**约束**:
- `Dst` 和 `Src` 必须大小相同
- 两者都必须是 trivially copyable

**典型用例**: SIMD 类型转换、浮点数位操作

## 内部实现细节

### 平台特定的 ABI 处理

模块定义了 `SK_FP_SAFE_ABI` 宏来处理 32 位 x86 平台的特殊情况:

```cpp
#if defined(_MSC_VER) && defined(_M_IX86)
    #define SK_FP_SAFE_ABI __vectorcall
#else
    #define SK_FP_SAFE_ABI
#endif
```

**问题背景**:
- 8 字节的 GCC/Clang 向量扩展类型在 32 位 x86 上会通过 MMX mm0 寄存器传递/返回
- 这会破坏 x87 FPU 的 st0 寄存器状态
- 32 位 x86 的默认调用约定通过 ST0 (x87 FPU) 返回浮点值,可能导致 NaN 位模式变异

**解决方案**:
- 使用 `SK_ALWAYS_INLINE` 强制内联,避免跨翻译单元的 ABI 问题
- MSVC 32 位使用 `__vectorcall` 通过 xmm0 寄存器返回

### 内存操作实现

所有内存操作都通过 `memcpy` 实现,编译器能将其优化为直接内存访问:

```cpp
memcpy(&val, static_cast<const void*>(ptr), sizeof(val));
```

这种方式:
- 避免了未定义行为 (指针别名问题)
- 支持非对齐访问
- 编译器能识别并优化为高效的汇编指令

### 类型安全保障

使用 `static_assert` 确保类型安全:

```cpp
static_assert(std::is_trivially_copyable_v<T>);
static_assert(sizeof(Dst) == sizeof(Src));
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `<cstring>` | memcpy 函数 |
| `<type_traits>` | 类型特征检查 |
| `include/private/base/SkAttributes.h` | SK_ALWAYS_INLINE 等宏定义 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| SkVx.h | SIMD 向量类型转换 |
| SkZip.h | 迭代器内部数据访问 |
| 所有 codec 模块 | 图像数据解析和转换 |
| 图形渲染管线 | 像素数据处理 |

## 设计模式与设计决策

### 1. 模板元编程

使用模板函数提供类型安全的泛型实现,编译时展开,零运行时开销。

### 2. 强制内联策略

通过 `SK_ALWAYS_INLINE` 确保函数内联,原因:
- 避免 ABI 问题(特别是 32 位 x86)
- 让编译器识别并优化 memcpy 模式
- 防止 ODR 违规

### 3. 命名空间封装

使用命名空间 `SkHexadecimalDigits` 避免全局命名空间污染,同时保持常量的编译时初始化。

### 4. 安全的类型转换

使用 `memcpy` 而非 union 或 reinterpret_cast 进行位转换,符合 C++ 标准,避免严格别名规则问题。

## 性能考量

### 1. 零开销抽象

所有函数都是内联的模板函数,编译后不产生额外的函数调用开销。

### 2. 编译器优化友好

`memcpy` 模式能被现代编译器识别并优化为:
- x86: `movdqu` (非对齐移动)
- ARM: `vld1/vst1` (NEON 加载/存储)
- 直接寄存器操作

### 3. 缓存友好性

通过非对齐加载支持,可以避免不必要的数据重新对齐复制,减少内存带宽消耗。

### 4. 平台特定优化

针对不同平台选择最优的 ABI 和调用约定,避免寄存器状态污染。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/base/SkVx.h` | 使用者 | SIMD 向量类使用 sk_bit_cast |
| `src/base/SkZip.h` | 使用者 | 迭代器使用内存工具 |
| `include/private/base/SkAttributes.h` | 依赖 | 提供 SK_ALWAYS_INLINE 宏 |
| `src/codec/*` | 使用者 | 图像解码中的数据转换 |
| `src/core/SkRasterPipeline.cpp` | 使用者 | 像素管道中的位操作 |
