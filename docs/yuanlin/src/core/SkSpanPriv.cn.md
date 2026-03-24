# SkSpanPriv

> 源文件
> - src/core/SkSpanPriv.h

## 概述

`SkSpanPriv` 是 Skia 内部使用的 `SkSpan` 辅助工具类,提供了两个核心功能:范围相等性比较(`EQ`)和内存复制(`Copy`)。该类是纯静态工具类,封装了对 `SkSpan`(Skia 的轻量级数组视图)的常用操作,通过模板实现类型安全的通用算法。

## 架构位置

`SkSpanPriv` 位于 Skia 核心工具层:

- **实用工具层**: 与 `SkTArray`、`SkTDArray` 等容器辅助类并列
- **内部接口**: 仅供 Skia 内部使用(位于 `src/core/`)
- **模板库**: 基于标准库 `<algorithm>` 的轻量封装

## 主要类与结构体

### SkSpanPriv (静态工具类)

**继承关系**: 无继承

**关键成员变量**: 无(纯静态类)

**静态方法**:

| 方法 | 说明 |
|------|------|
| `EQ<T>(SkSpan<T> a, SkSpan<T> b)` | 比较两个 span 是否相等 |
| `Copy<T>(SkSpan<T> dst, SkSpan<const T> src)` | 安全地复制 span 内容 |

## 公共 API 函数

### EQ - 范围相等性比较

```cpp
template <typename T>
static bool EQ(SkSpan<T> a, SkSpan<T> b);
```

**功能**: 判断两个 span 是否包含相同内容

**实现**:
```cpp
template <typename T>
static bool EQ(SkSpan<T> a, SkSpan<T> b) {
    if (a.size() != b.size()) {
        return false;  // 大小不同
    }
    if (a.empty()) {
        return true;   // 都为空
    }
    // 指针相同或内容相同
    return (a.data() == b.data()) || std::equal(a.begin(), a.end(), b.begin());
}
```

**优化点**:
1. **快速大小检查**: 大小不等立即返回 `false`
2. **空检查**: 空 span 直接返回 `true`
3. **指针相同优化**: 同一内存区域无需逐元素比较
4. **标准库优化**: 使用 `std::equal`,可能利用 SIMD

### Copy - 安全内存复制

```cpp
template <typename T>
static void Copy(SkSpan<T> dst, SkSpan<const T> src);
```

**功能**: 将源 span 的内容复制到目标 span

**实现**:
```cpp
template <typename T>
static void Copy(SkSpan<T> dst, SkSpan<const T> src) {
    SkASSERT(dst.size() == src.size());  // 断言大小匹配
    sk_careful_memcpy(dst.data(), src.data(), src.size_bytes());
}
```

**安全性**:
- **大小检查**: 断言确保目标有足够空间
- **重叠检测**: `sk_careful_memcpy` 处理内存重叠情况
- **类型安全**: 模板确保类型匹配

## 内部实现细节

### EQ 实现分析

```cpp
template <typename T>
static bool EQ(SkSpan<T> a, SkSpan<T> b) {
    // 1. 大小检查 (O(1))
    if (a.size() != b.size()) {
        return false;
    }

    // 2. 空检查 (O(1))
    if (a.empty()) {
        return true;
    }

    // 3. 指针优化 (O(1))
    if (a.data() == b.data()) {
        return true;  // 指向同一内存
    }

    // 4. 逐元素比较 (O(n))
    return std::equal(a.begin(), a.end(), b.begin());
}
```

**性能特性**:
- **最好情况**: O(1) (大小不同或指针相同)
- **最坏情况**: O(n) (需要逐元素比较)
- **平均情况**: 通常 O(1) (大小或指针优化)

### sk_careful_memcpy 说明

```cpp
// 定义在 include/private/base/SkMalloc.h
void sk_careful_memcpy(void* dst, const void* src, size_t len) {
    if (dst != src && len > 0) {
        // 检测内存重叠
        if ((char*)dst < (char*)src) {
            memcpy(dst, src, len);  // 正向复制
        } else if ((char*)dst > (char*)src + len ||
                   (char*)src > (char*)dst + len) {
            memcpy(dst, src, len);  // 无重叠
        } else {
            memmove(dst, src, len);  // 有重叠,使用 memmove
        }
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkSpan` | 被操作的主要类型 |
| `SkMalloc` | `sk_careful_memcpy` 实现 |
| `<algorithm>` | `std::equal` 标准算法 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| 容器实现 | `SkTArray`、`SkTDArray` 等可能使用 |
| 序列化 | 数据比较和复制 |
| 图像处理 | 像素数据批量操作 |

## 设计模式与设计决策

### 1. 静态工具类模式

```cpp
class SkSpanPriv {
public:
    // 只提供静态方法,无实例化
    template <typename T> static bool EQ(...);
    template <typename T> static void Copy(...);
};
```

**优点**:
- 无状态,无需实例化
- 明确的作用域(SkSpanPriv::)
- 避免命名冲突

### 2. 泛型编程

使用模板支持任意类型:

```cpp
template <typename T> static bool EQ(SkSpan<T> a, SkSpan<T> b);
// 支持: int, float, SkPoint, 自定义类型等
```

### 3. 设计权衡

**为什么不使用 operator==?**

```cpp
// 不这样做:
bool operator==(SkSpan<T> a, SkSpan<T> b) { ... }

// 而是:
bool SkSpanPriv::EQ(SkSpan<T> a, SkSpan<T> b) { ... }
```

**原因**:
- **内部使用**: `SkSpanPriv` 明确标识为内部工具
- **避免污染**: 不向全局命名空间添加运算符
- **显式调用**: `EQ` 比 `==` 更明确意图

**为什么需要 Copy 而不直接用 memcpy?**

| 方面 | 直接 memcpy | SkSpanPriv::Copy |
|------|-------------|------------------|
| 大小检查 | 手动 | 自动断言 |
| 重叠检测 | 容易出错 | 自动处理 |
| 类型安全 | 需要 sizeof 计算 | 模板自动 |
| 可读性 | 底层 | 高层抽象 |

## 性能考量

### 1. 内联优化

静态模板函数通常会被内联:

```cpp
// 调用点
if (SkSpanPriv::EQ(spanA, spanB)) { ... }

// 编译后可能内联为:
if (spanA.size() != spanB.size() ? false :
    spanA.empty() ? true :
    spanA.data() == spanB.data() ? true :
    std::equal(spanA.begin(), spanA.end(), spanB.begin())) { ... }
```

### 2. SIMD 加速

`std::equal` 在现代编译器中可能使用 SIMD:

```cpp
// GCC/Clang 可能生成 SSE/AVX 代码
std::equal(a.begin(), a.end(), b.begin());

// 等价于(伪代码):
__m128i va = _mm_loadu_si128(a.data());
__m128i vb = _mm_loadu_si128(b.data());
__m128i cmp = _mm_cmpeq_epi32(va, vb);
```

### 3. 分支预测优化

常见情况优先检查:

```cpp
// 最常见: 大小不同
if (a.size() != b.size()) return false;

// 次常见: 指针相同
if (a.data() == b.data()) return true;

// 最慢路径: 逐元素比较
return std::equal(...);
```

### 4. 零拷贝场景

```cpp
// 拷贝前检查,避免不必要的操作
if (!SkSpanPriv::EQ(dst, src)) {
    SkSpanPriv::Copy(dst, src);
}
```

### 5. 性能对比

| 操作 | 手动实现 | SkSpanPriv |
|------|---------|-----------|
| 相等性比较 | ~10 行代码 | 1 行调用 |
| 安全复制 | ~5 行 + 重叠检查 | 1 行调用 |
| 编译器优化 | 可能较差 | 充分优化 |
| 错误率 | 高 | 低(经过测试) |

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkSpanPriv.h` | 本文件(span 工具函数) |
| `include/core/SkSpan.h` | `SkSpan` 类定义 |
| `include/private/base/SkMalloc.h` | `sk_careful_memcpy` 实现 |
| `src/core/SkTArray.h` | 可能的使用者 |
| `src/core/SkTDArray.h` | 可能的使用者 |
