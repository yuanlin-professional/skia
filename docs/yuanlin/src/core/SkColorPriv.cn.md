# SkColorPriv

> 源文件: src/core/SkColorPriv.h

## 概述

`SkColorPriv.h` 是 Skia 最底层的颜色操作头文件,定义了基础的颜色数据类型、位移和掩码常量、以及最基本的颜色操作函数。该文件处理平台字节序差异,定义了 `SkPMColor` 的实际内存布局(RGBA 或 BGRA),并提供了 alpha 混合、颜色打包等核心操作。所有高层颜色操作最终都依赖这些基础定义。

## 架构位置

`SkColorPriv.h` 位于 Skia 核心层(src/core),是私有实现头文件中最底层的一个。它直接依赖于 CPU 类型定义和基础数学工具,被所有需要进行像素级操作的模块使用,包括 `SkColorData.h`、混合器、光栅化器等。

## 主要类与结构体

该文件主要定义宏、内联函数和一个辅助类。

### SkColorConverter

颜色转换辅助类,用于批量转换 `SkColor` 到 `SkColor4f`:

| 特性 | 说明 |
|------|------|
| 用途 | 批量颜色格式转换 |
| 存储 | 使用 `STArray<2, SkColor4f>` |

**方法:**
```cpp
SkColorConverter(SkSpan<const SkColor>);  // 构造
SkSpan<SkColor4f> colors4f();             // 获取转换结果
```

## 公共 API 函数

### Alpha 操作

**255 到 256 转换:**
```cpp
static inline unsigned SkAlpha255To256(U8CPU alpha);
```
- 将 [0, 255] 转换到 [0, 256]
- 实现: `alpha + 1`
- 用于避免除法,使用位移代替

**Alpha 乘法:**
```cpp
#define SkAlphaMul(value, alpha256)  (((value) * (alpha256)) >> 8)
```
- 计算 `value * alpha256 / 256`
- 使用位移代替除法

### 单位标量转换

```cpp
static inline U8CPU SkUnitScalarClampToByte(SkScalar x);
```
- 将 [0.0, 1.0] 标量转换到 [0, 255] 字节
- 包含钳位和四舍五入
- 实现: `(int)(SkTPin(x, 0.0f, 1.0f) * 255 + 0.5f)`

### 32位颜色常量

**位宽定义:**
```cpp
#define SK_A32_BITS     8
#define SK_R32_BITS     8
#define SK_G32_BITS     8
#define SK_B32_BITS     8
```

**掩码定义:**
```cpp
#define SK_A32_MASK     ((1 << SK_A32_BITS) - 1)  // 0xFF
#define SK_R32_MASK     ((1 << SK_R32_BITS) - 1)  // 0xFF
// ...
```

### 字节序处理

**RGBA 布局:**
```cpp
#define SK_RGBA_R32_SHIFT   0
#define SK_RGBA_G32_SHIFT   8
#define SK_RGBA_B32_SHIFT   16
#define SK_RGBA_A32_SHIFT   24
```

**BGRA 布局:**
```cpp
#define SK_BGRA_B32_SHIFT   0
#define SK_BGRA_G32_SHIFT   8
#define SK_BGRA_R32_SHIFT   16
#define SK_BGRA_A32_SHIFT   24
```

**平台选择:**
- 根据 `SK_R32_SHIFT` 的值推导 `SK_PMCOLOR_IS_RGBA` 或 `SK_PMCOLOR_IS_BGRA`
- 在编译时确定,运行时无开销

**验证:**
```cpp
#if (SK_A32_SHIFT == SK_RGBA_A32_SHIFT && ...)
    #define SK_PMCOLOR_IS_RGBA
#elif (SK_A32_SHIFT == SK_BGRA_A32_SHIFT && ...)
    #define SK_PMCOLOR_IS_BGRA
#else
    #error "need 32bit packing to be either RGBA or BGRA"
#endif
```

### 通道提取

```cpp
#define SkGetPackedA32(packed)  ((uint32_t)((packed) << (24 - SK_A32_SHIFT)) >> 24)
#define SkGetPackedR32(packed)  ((uint32_t)((packed) << (24 - SK_R32_SHIFT)) >> 24)
#define SkGetPackedG32(packed)  ((uint32_t)((packed) << (24 - SK_G32_SHIFT)) >> 24)
#define SkGetPackedB32(packed)  ((uint32_t)((packed) << (24 - SK_B32_SHIFT)) >> 24)
```

**工作原理:**
- 使用左移将目标通道移到最高字节
- 使用无符号右移将其移到最低字节
- 自动清除其他通道

### 断言宏

```cpp
#define SkA32Assert(a)  SkASSERT((unsigned)(a) <= SK_A32_MASK)
#define SkR32Assert(r)  SkASSERT((unsigned)(r) <= SK_R32_MASK)
#define SkG32Assert(g)  SkASSERT((unsigned)(g) <= SK_G32_MASK)
#define SkB32Assert(b)  SkASSERT((unsigned)(b) <= SK_B32_MASK)
```

### 颜色打包

**ARGB32 打包:**
```cpp
static inline SkPMColor SkPackARGB32(U8CPU a, U8CPU r, U8CPU g, U8CPU b);
```
- 组合四个 8 位通道为 32 位颜色
- 包含调试断言验证输入范围
- 实现:
  ```cpp
  return (a << SK_A32_SHIFT) | (r << SK_R32_SHIFT) |
         (g << SK_G32_SHIFT) | (b << SK_B32_SHIFT);
  ```

**预乘 ARGB32:**
```cpp
static inline SkPMColor SkPremultiplyARGBInline(U8CPU a, U8CPU r, U8CPU g, U8CPU b);
```
- 组合并预乘颜色
- 仅在 alpha < 255 时进行乘法
- 使用 `SkMulDiv255Round` 保证正确的舍入

### Alpha 混合

**Alpha 乘法(快速版):**
```cpp
static SK_ALWAYS_INLINE uint32_t SkAlphaMulQ(uint32_t c, unsigned scale);
```
- 同时对所有通道应用 alpha 缩放
- 使用掩码技巧分离和合并通道
- 强制内联以提高性能

**SrcOver 混合:**
```cpp
static inline SkPMColor SkPMSrcOver(SkPMColor src, SkPMColor dst);
```
- 实现标准的 Porter-Duff SrcOver 模式
- 公式: `src + dst * (1 - src.alpha)`
- 包含通道饱和处理

## 内部实现细节

### 字节序自动检测

编译时根据位移定义推导字节序:

```cpp
#if (SK_A32_SHIFT == SK_RGBA_A32_SHIFT && ...)
    #define SK_PMCOLOR_IS_RGBA
#elif (SK_A32_SHIFT == SK_BGRA_A32_SHIFT && ...)
    #define SK_PMCOLOR_IS_BGRA
#else
    #error "need 32bit packing to be either RGBA or BGRA"
#endif
```

这确保:
- 一次编译仅支持一种字节序
- 运行时无分支
- 与 GPU 后端的字节序匹配

### SkAlphaMulQ 实现

```cpp
static SK_ALWAYS_INLINE uint32_t SkAlphaMulQ(uint32_t c, unsigned scale) {
    static constexpr uint32_t kMask = 0x00FF00FF;

    uint32_t rb = ((c & kMask) * scale) >> 8;
    uint32_t ag = ((c >> 8) & kMask) * scale;
    return (rb & kMask) | (ag & ~kMask);
}
```

**技巧:**
- 分离 R/B 和 A/G 通道
- 同时乘以缩放因子
- 使用掩码合并结果
- 避免分支和循环

### SkPMSrcOver 实现

```cpp
static inline SkPMColor SkPMSrcOver(SkPMColor src, SkPMColor dst) {
    uint32_t scale = SkAlpha255To256(255 - SkGetPackedA32(src));

    static constexpr uint32_t kMask = 0x00FF00FF;
    uint32_t rb = (((dst & kMask) * scale) >> 8) & kMask;
    uint32_t ag = (((dst >> 8) & kMask) * scale) & ~kMask;

    rb += (src &  kMask);
    ag += (src & ~kMask);

    // 饱和处理
    return std::min(rb & 0x000001FF, 0x000000FFU) |
           std::min(ag & 0x0001FF00, 0x0000FF00U) |
           std::min(rb & 0x01FF0000, 0x00FF0000U) |
                   (ag & 0xFF000000);
}
```

**特性:**
- 使用 256 级缩放避免除法
- 分离 R/B 和 A/G 通道同时处理
- 饱和处理防止溢出
- Alpha 通道不需要饱和(数学保证)

### SkPremultiplyARGBInline 实现

```cpp
static inline SkPMColor SkPremultiplyARGBInline(U8CPU a, U8CPU r, U8CPU g, U8CPU b) {
    if (a != 255) {
        r = SkMulDiv255Round(r, a);
        g = SkMulDiv255Round(g, a);
        b = SkMulDiv255Round(b, a);
    }
    return SkPackARGB32(a, r, g, b);
}
```

**正确舍入:**
- 使用 `SkMulDiv255Round` 而不是简单的 `(r * a) / 255`
- 保证 `premul(255, 255, 255, 255) == (255, 255, 255, 255)`
- 避免精度损失

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkColor` | 基础颜色类型 |
| `SkTypes` | 基础类型定义 |
| `SkCPUTypes` | 字节序定义 |
| `SkMath` | `SkMulDiv255Round` 等 |
| `SkTPin` | 钳位函数 |
| `SkTArray` | `SkColorConverter` 存储 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| `SkColorData.h` | 构建在此之上 |
| 所有光栅化器 | 像素级操作 |
| 所有混合器 | Alpha 混合 |
| 位图操作 | 颜色格式转换 |
| 着色器 | 颜色生成 |

## 设计模式与设计决策

### 编译时字节序选择

在编译时确定字节序:
- 运行时零开销
- 避免条件分支
- 与平台和 GPU 后端匹配

### 宏和内联混合

- 简单操作使用宏(如 `SkAlphaMul`)
- 复杂操作使用内联函数(如 `SkPackARGB32`)
- 调试模式使用内联函数以包含断言

### 强制内联

关键函数使用 `SK_ALWAYS_INLINE`:
```cpp
static SK_ALWAYS_INLINE uint32_t SkAlphaMulQ(...);
```
- 在优化体积的构建中也保证内联
- 对性能关键路径至关重要
- 编译器可能不自动内联的小函数

### 位操作优化

使用位操作而不是算术运算:
- 位移代替除法/乘法
- 掩码代替条件判断
- 利用 CPU 的位操作指令

## 性能考量

### 避免除法

使用 256 级缩放代替 255 级:
```cpp
(value * alpha256) >> 8  // 快速
(value * alpha255) / 255  // 慢
```

### SIMD 友好

许多操作使用掩码同时处理多个通道:
- 为向量化提供基础
- 减少指令数
- 提高 ILP(指令级并行)

### 缓存友好

紧凑的数据表示:
- `SkPMColor`: 4 字节
- 无填充或对齐浪费
- 批量操作局部性好

### 分支消除

使用掩码和位操作避免分支:
- 减少分支预测失败
- 适合流水线执行
- SIMD 向量化友好

### 调试与发布平衡

- 调试模式: 内联函数 + 断言
- 发布模式: 宏(更快,但无断言)
- 通过预处理器自动选择

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkColor.h` | 基础 | 公共颜色类型 |
| `include/core/SkTypes.h` | 依赖 | 基础类型 |
| `include/private/base/SkCPUTypes.h` | 依赖 | 字节序定义 |
| `include/private/base/SkMath.h` | 依赖 | 数学工具 |
| `src/core/SkColorData.h` | 使用者 | 高层颜色操作 |
| `src/core/SkBlitter.h` | 使用者 | 混合器 |
| `src/opts/` | 相关 | SIMD 优化版本 |
