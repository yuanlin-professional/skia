# SkFDot6

> 源文件
> - src/core/SkFDot6.h

## 概述

`SkFDot6.h` 定义了 Skia 中用于字体光栅化和路径处理的固定点数学类型和操作。`SkFDot6` 是一个 26.6 固定点格式的整数类型,其中 6 位用于小数部分,26 位用于整数部分。这种格式在字体渲染和扫描线转换中广泛使用,因为它在保持亚像素精度的同时避免了浮点运算的开销。

该文件提供了一系列宏和内联函数,用于在不同数值表示之间转换(整数、浮点、`SkFixed`、`SkFDot6`),以及对 `SkFDot6` 值进行取整、取上限、取下限等操作。这些工具函数是 Skia 字形缓存、边缘构建和扫描线渲染的基础。

## 架构位置

`SkFDot6` 在 Skia 字体和路径光栅化管线中处于底层数学支持层:

```
上层字体/路径 API
    ↓
字形度量和路径坐标(浮点)
    ↓
SkFDot6 转换(浮点→固定点)
    ↓
扫描线转换(使用 SkFDot6 坐标)
    ↓
像素坐标(整数)
```

**使用场景**:
- 字形边缘构建(SkEdge, SkAnalyticEdge)
- 扫描线渲染坐标计算
- 亚像素定位精度
- 字体提示(hinting)计算

## 主要类与结构体

### SkFDot6 类型

**类型定义**:
```cpp
typedef int32_t SkFDot6;
```

**格式**: 26.6 固定点数
- 整数部分: 26 位(符号位 + 25 位有效整数)
- 小数部分: 6 位
- 最小单位: 1/64 = 0.015625

**范围**:
- 最大值: (2^25 - 1) + 63/64 ≈ 33,554,431.984375
- 最小值: -(2^25) ≈ -33,554,432
- 精度: 1/64 像素

### 常量定义

| 常量 | 值 | 含义 |
|------|----|----|
| `SK_FDot6One` | 64 | FDot6 格式的 1.0 |
| `SK_FDot6Half` | 32 | FDot6 格式的 0.5 |

## 公共 API 函数

### 转换函数

#### 整数转换

```cpp
#ifdef SK_DEBUG
    constexpr inline SkFDot6 SkIntToFDot6(int x);
#else
    #define SkIntToFDot6(x) ((x) << 6)
#endif
```
- **功能**: 将整数转换为 FDot6 格式
- **实现**: 左移 6 位(乘以 64)
- **Debug 版本**: 包含溢出检查
- **范围检查**: 确保 `x` 在 `[-(2^25), 2^25-1]` 范围内

#### 浮点转换

```cpp
#define SkFloatToFDot6(x)  (SkFDot6)((x) * SK_FDot6One)
#define SkScalarToFDot6    SkFloatToFDot6
```
- **功能**: 将浮点数转换为 FDot6 格式
- **实现**: 乘以 64 并转换为整数
- **精度损失**: 小数部分被截断到 1/64 精度

```cpp
#define SkFDot6ToFloat(x)  ((float)(x) * 0.015625f)
#define SkFDot6ToScalar    SkFDot6ToFloat
```
- **功能**: 将 FDot6 格式转换为浮点数
- **实现**: 除以 64(乘以 1/64 = 0.015625)

#### SkFixed 转换

```cpp
#define SkFixedToFDot6(x)   ((x) >> 10)
```
- **功能**: 将 SkFixed(16.16)转换为 FDot6(26.6)
- **实现**: 右移 10 位(除以 1024,即从 16 位小数降到 6 位)
- **精度损失**: 丢失 10 位小数精度

```cpp
inline SkFixed SkFDot6ToFixed(SkFDot6 x) {
    SkASSERT((SkLeftShift(x, 10) >> 10) == x);
    return SkLeftShift(x, 10);
}
```
- **功能**: 将 FDot6(26.6)转换为 SkFixed(16.16)
- **实现**: 左移 10 位(乘以 1024)
- **断言**: 检查是否会溢出

### 取整函数

```cpp
#define SkFDot6Floor(x)     ((x) >> 6)
```
- **功能**: 向下取整到最接近的整数
- **实现**: 右移 6 位,丢弃小数部分
- **示例**: `SkFDot6Floor(195)` → `3` (195/64 = 3.046875)

```cpp
#define SkFDot6Ceil(x)      (((x) + 63) >> 6)
```
- **功能**: 向上取整到最接近的整数
- **实现**: 加 63(几乎一个单位)后右移 6 位
- **示例**: `SkFDot6Ceil(193)` → `4` (193/64 = 3.015625, 向上取 4)

```cpp
#define SkFDot6Round(x)     (((x) + SK_FDot6Half) >> 6)
```
- **功能**: 四舍五入到最接近的整数
- **实现**: 加 0.5(32/64)后右移 6 位
- **示例**: `SkFDot6Round(192)` → `3`, `SkFDot6Round(224)` → `4`

### 除法函数

```cpp
inline SkFixed SkFDot6Div(SkFDot6 a, SkFDot6 b) {
    SkASSERT(b != 0);

    if (SkTFitsIn<int16_t>(a)) {
        return SkLeftShift(a, 16) / b;
    } else {
        return SkFixedDiv(a, b);
    }
}
```
- **功能**: 计算 `a / b`,返回 SkFixed(16.16)格式
- **优化**: 如果 `a` 适合 16 位,使用快速路径(避免 64 位除法)
- **回退**: 大数值使用 `SkFixedDiv`(可能涉及 64 位运算)

### 特殊舍入函数

```cpp
inline SkFDot6 SkScalarRoundToFDot6(SkScalar x, int shift)
{
    union {
        double  fDouble;
        int32_t fBits[2];
    } tmp;
    int fractionalBits = 6 + shift;
    double magic = (1LL << (52 - (fractionalBits))) * 1.5;

    tmp.fDouble = SkScalarToDouble(x) + magic;
#ifdef SK_CPU_BENDIAN
    return tmp.fBits[1];
#else
    return tmp.fBits[0];
#endif
}
```
- **功能**: 高效地将浮点数舍入到 FDot6 格式
- **技术**: 使用 "magic number" 技巧(banker's rounding)
- **参数**: `shift` - 额外的位移量,用于不同的固定点格式
- **舍入模式**: 银行家舍入(四舍六入五成双)

**原理**:
1. 利用 IEEE 754 双精度浮点数的尾数表示
2. 加上特定的 "magic number" 后,小数部分被移到整数位
3. 直接提取整数部分(通过 union 访问位表示)
4. 避免了分支和浮点取整指令

## 内部实现细节

### 固定点格式选择

**为什么是 26.6 而不是其他格式?**

1. **精度**: 6 位小数 = 1/64 精度,足够亚像素定位
2. **范围**: 26 位整数部分支持 ±3300 万像素坐标
3. **兼容性**: 与 FreeType 的 FT_F26Dot6 兼容
4. **运算**: 简单的位移操作,无需浮点单元

**与 SkFixed(16.16)的关系**:
- `SkFixed`: 用于通用的固定点运算,更高精度
- `SkFDot6`: 用于扫描线转换,更大范围

### Debug 模式的溢出检查

```cpp
#ifdef SK_DEBUG
    constexpr inline SkFDot6 SkIntToFDot6(int x) {
        SkASSERT(     (std::numeric_limits<SkFDot6>::min() >> 6) <= x &&
                 x <= (std::numeric_limits<SkFDot6>::max() >> 6));
        return x << 6;
    }
#endif
```

**检查条件**:
- 最小值: `-2^25` ≈ -33,554,432
- 最大值: `2^25 - 1` ≈ 33,554,431
- **原因**: 确保左移 6 位后不会溢出 32 位整数

### SkFDot6Div 的优化策略

```cpp
if (SkTFitsIn<int16_t>(a)) {
    return SkLeftShift(a, 16) / b;  // 快速路径
} else {
    return SkFixedDiv(a, b);        // 通用路径(64位)
}
```

**快速路径条件**: `a` 适合 int16_t(-32768 到 32767)
- **原因**: `a << 16` 不会超过 int32_t 范围
- **性能**: 32 位除法比 64 位快

**通用路径**: `SkFixedDiv`
- 实现可能使用 int64_t 中间值
- 处理大数值情况

### 位操作的安全性

```cpp
inline SkFixed SkFDot6ToFixed(SkFDot6 x) {
    SkASSERT((SkLeftShift(x, 10) >> 10) == x);  // 检查无信息丢失
    return SkLeftShift(x, 10);
}
```

**断言意义**:
- 确保 `x` 左移 10 位后不会溢出
- 右移后能恢复原值表示无信息丢失
- 防止静默的数值错误

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkScalar` | 浮点数类型定义 |
| `SkFixed` | 16.16 固定点类型 |
| `SkMath` | 数学辅助函数(如 `SkLeftShift`) |
| `SkTo` | 类型转换检查(如 `SkTFitsIn`) |
| `<limits>` | 数值极限查询 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| `SkEdge` | 使用 FDot6 坐标表示边缘 |
| `SkAnalyticEdge` | 使用 FDot6 进行分析边缘计算 |
| `SkScan` | 扫描线转换使用 FDot6 坐标 |
| `SkGlyph` | 字形位置使用 FDot6 亚像素定位 |
| `SkStrike` | 字形缓存键生成使用 FDot6 |

## 设计模式与设计决策

### 宏 vs 内联函数

**使用宏的情况**:
```cpp
#define SkFDot6Floor(x)     ((x) >> 6)
#define SkFloatToFDot6(x)  (SkFDot6)((x) * SK_FDot6One)
```
- **优势**: 零开销,编译时展开
- **劣势**: 无类型检查,可能重复求值

**使用内联函数的情况**:
```cpp
inline SkFixed SkFDot6Div(SkFDot6 a, SkFDot6 b) { ... }
inline SkFixed SkFDot6ToFixed(SkFDot6 x) { ... }
```
- **优势**: 类型安全,可以添加断言
- **劣势**: 稍微复杂的语法

**设计决策**: 简单操作用宏,复杂逻辑用内联函数

### 条件编译策略

```cpp
#ifdef SK_DEBUG
    constexpr inline SkFDot6 SkIntToFDot6(int x) {
        SkASSERT(...);  // 范围检查
        return x << 6;
    }
#else
    #define SkIntToFDot6(x) ((x) << 6)
#endif
```

**原因**:
- **Debug**: 提供溢出检查,帮助发现错误
- **Release**: 使用宏,零开销

### Magic Number 舍入技术

`SkScalarRoundToFDot6` 使用的技巧:

**优势**:
- 避免浮点舍入指令(可能较慢)
- 避免分支(if-else 判断)
- 在支持的平台上非常高效

**劣势**:
- 代码可读性差
- 依赖 IEEE 754 浮点表示
- 大端/小端需要不同处理

**来源**: [Cairo 的实现](http://stereopsis.com/sree/fpu2006.html)

### 设计决策总结

1. **26.6 格式选择**: 平衡精度、范围和兼容性
2. **宏大量使用**: 性能关键代码,避免函数调用开销
3. **条件断言**: Debug 模式检查,Release 模式无开销
4. **平台适配**: 大端/小端的不同处理
5. **优化路径**: `SkFDot6Div` 根据输入大小选择快速/通用路径

## 性能考量

### 位操作效率

```cpp
SkFDot6Floor(x)  → (x >> 6)     // 1 个位移指令
SkIntToFDot6(x)  → (x << 6)     // 1 个位移指令
```
- CPU 原生指令,1-2 个时钟周期
- 比浮点除法/乘法快数倍

### 避免浮点运算

在扫描线转换中使用 FDot6:
```cpp
// 慢: 浮点运算
float x = x0 + t * dx;

// 快: 固定点运算
SkFDot6 x = x0 + SkFixedMul(t, dx);
```

### 快速舍入

`SkScalarRoundToFDot6` 性能:
- 无分支(branch-free)
- 可能比 `floorf/ceilf` 快 2-3 倍
- 适合批量转换

### 内存占用

```cpp
sizeof(SkFDot6) == 4 bytes
```
- 与 float 相同大小
- 缓存友好
- 适合大量坐标存储

### 精度权衡

**精度损失**:
- FDot6 精度: 1/64 ≈ 0.0156 像素
- 对于大多数显示器,亚像素精度足够

**性能收益**:
- 整数运算比浮点快(在没有 FPU 或旧硬件上尤其明显)
- 固定点坐标便于扫描线算法

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/base/SkFixed.h` | 依赖 | SkFixed(16.16)类型定义 |
| `include/core/SkScalar.h` | 依赖 | SkScalar 浮点类型 |
| `include/private/base/SkMath.h` | 依赖 | 数学辅助函数 |
| `include/private/base/SkTo.h` | 依赖 | 类型转换检查 |
| `src/core/SkEdge.h` | 使用者 | 边缘数据结构 |
| `src/core/SkAnalyticEdge.h` | 使用者 | 分析边缘数据结构 |
| `src/core/SkScan.cpp` | 使用者 | 扫描线转换实现 |
| `src/core/SkGlyph.h` | 使用者 | 字形数据结构 |
