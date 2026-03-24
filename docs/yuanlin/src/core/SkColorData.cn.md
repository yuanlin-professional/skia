# SkColorData

> 源文件: src/core/SkColorData.h

## 概述

`SkColorData.h` 是 Skia 核心色彩数据操作的低层头文件,提供了大量用于颜色格式转换、通道提取、混合运算和像素格式操作的内联函数和宏定义。该文件定义了 RGB565、ARGB4444、ARGB8888 等多种像素格式的操作,以及它们之间的快速转换方法。这些工具函数是 Skia 光栅化引擎的基础,被广泛用于像素级操作。

## 架构位置

`SkColorData.h` 位于 Skia 核心层(src/core),是私有实现头文件。它构建在 `SkColorPriv.h` 之上,提供更高层的颜色数据操作。该文件被光栅化器、混合器、着色器等底层组件广泛使用,是性能关键路径上的核心工具集。

## 主要类与结构体

该文件主要定义宏、内联函数和类型别名,不定义具体的类。

### 类型定义

```cpp
typedef uint16_t SkPMColor16;    // 16位预乘颜色
using SkPMColor4f = SkRGBA4f<kPremul_SkAlphaType>;  // 浮点预乘颜色
```

### 常量定义

```cpp
constexpr SkPMColor4f SK_PMColor4fTRANSPARENT = { 0, 0, 0, 0 };
constexpr SkPMColor4f SK_PMColor4fBLACK = { 0, 0, 0, 1 };
constexpr SkPMColor4f SK_PMColor4fWHITE = { 1, 1, 1, 1 };
constexpr SkPMColor4f SK_PMColor4fILLEGAL = { SK_FloatNegativeInfinity, ... };
```

## 公共 API 函数

### RGB565 格式操作

**位定义:**
```cpp
#define SK_R16_BITS     5
#define SK_G16_BITS     6
#define SK_B16_BITS     5
```

**通道提取:**
```cpp
#define SkGetPackedR16(color)   (((unsigned)(color) >> SK_R16_SHIFT) & SK_R16_MASK)
#define SkGetPackedG16(color)   (((unsigned)(color) >> SK_G16_SHIFT) & SK_G16_MASK)
#define SkGetPackedB16(color)   (((unsigned)(color) >> SK_B16_SHIFT) & SK_B16_MASK)
```

**打包:**
```cpp
static inline uint16_t SkPackRGB16(unsigned r, unsigned g, unsigned b);
```

**5/6位到8位扩展:**
```cpp
static inline unsigned SkR16ToR32(unsigned r);  // 5位->8位
static inline unsigned SkG16ToG32(unsigned g);  // 6位->8位
static inline unsigned SkB16ToB32(unsigned b);  // 5位->8位
```

实现使用位复制技术保持线性关系:
```cpp
return (r << (8 - SK_R16_BITS)) | (r >> (2 * SK_R16_BITS - 8));
// 0x1F (31) -> 0xFF (255)
```

### ARGB4444 格式操作

**移位定义:**
```cpp
#define SK_A4444_SHIFT    0
#define SK_R4444_SHIFT    12
#define SK_G4444_SHIFT    8
#define SK_B4444_SHIFT    4
```

**半字节扩展:**
```cpp
static inline U8CPU SkReplicateNibble(unsigned nib) {
    return (nib << 4) | nib;  // 0xF -> 0xFF
}
```

**转换:**
```cpp
static inline SkPMColor SkPixel4444ToPixel32(U16CPU c);
```

### 字节序处理

**红蓝交换:**
```cpp
static inline uint32_t SkSwizzle_RB(uint32_t c);
```

**RGBA/BGRA 打包:**
```cpp
static inline uint32_t SkPackARGB_as_RGBA(U8CPU a, U8CPU r, U8CPU g, U8CPU b);
static inline uint32_t SkPackARGB_as_BGRA(U8CPU a, U8CPU r, U8CPU g, U8CPU b);
```

**PMColor 交换:**
```cpp
static inline SkPMColor SkSwizzle_RGBA_to_PMColor(uint32_t c);
static inline SkPMColor SkSwizzle_BGRA_to_PMColor(uint32_t c);
```

### 亮度计算

```cpp
static inline U8CPU SkComputeLuminance(U8CPU r, U8CPU g, U8CPU b);
```

使用 ITU-R BT.709 系数:
```cpp
#define SK_LUM_COEFF_R (0.2126f)
#define SK_LUM_COEFF_G (0.7152f)
#define SK_LUM_COEFF_B (0.0722f)
```

实现使用定点运算:
```cpp
return (r * 54 + g * 183 + b * 19) >> 8;
```

### Alpha 混合

**Alpha 乘法逆:**
```cpp
static inline U16CPU SkAlphaMulInv256(U16CPU value, U16CPU alpha256);
```
计算 `256 - (value * alpha256) / 255`,范围 [0, 256]。

**Alpha 混合:**
```cpp
static inline int SkAlphaBlend(int src, int dst, int scale256);
```
实现: `dst + SkAlphaMul(src - dst, scale256)`

### 四字节插值

**标准插值(256 级):**
```cpp
static inline SkPMColor SkFourByteInterp256(SkPMColor src, SkPMColor dst, int scale);
```
- scale = 0 返回 dst
- scale = 256 返回 src

**标准插值(255 级):**
```cpp
static inline SkPMColor SkFourByteInterp(SkPMColor src, SkPMColor dst, U8CPU srcWeight);
```
- srcWeight = 0 返回 dst
- srcWeight = 255 返回 src

**快速插值(32位优化):**
```cpp
static inline SkPMColor SkFastFourByteInterp256_32(SkPMColor src, SkPMColor dst, unsigned scale);
```

使用分离 alpha/green 和 red/blue 的技巧:
```cpp
uint32_t src_ag, src_rb, dst_ag, dst_rb;
SkSplay(src, &src_ag, &src_rb);  // 分离通道
const uint32_t ret_ag = src_ag * scale + (256 - scale) * dst_ag;
const uint32_t ret_rb = src_rb * scale + (256 - scale) * dst_rb;
return SkUnsplay(ret_ag, ret_rb);  // 合并通道
```

**快速插值(64位优化):**
```cpp
static inline SkPMColor SkFastFourByteInterp256_64(SkPMColor src, SkPMColor dst, unsigned scale);
```

使用 64 位一次性混合四个通道:
```cpp
return SkUnsplay(SkSplay(src) * scale + (256-scale) * SkSplay(dst));
```

### Splay/Unsplay 操作

**分离通道:**
```cpp
static inline void SkSplay(uint32_t color, uint32_t* ag, uint32_t* rb);
```
- 0xAARRGGBB -> ag=0x00AA00GG, rb=0x00RR00BB

```cpp
static inline uint64_t SkSplay(uint32_t color);
```
- 0xAARRGGBB -> 0x00AA00GG00RR00BB (注意:ARGB -> AGRB)

**合并通道:**
```cpp
static inline uint32_t SkUnsplay(uint32_t ag, uint32_t rb);
static inline uint32_t SkUnsplay(uint64_t agrb);
```

### SrcOver 混合

```cpp
static inline SkPMColor SkPMSrcOver(SkPMColor src, SkPMColor dst);
```

实现标准的 SrcOver 混合模式:
```cpp
scale = 256 - src.alpha;
result = src + dst * scale / 256;
```

包含通道饱和处理:
```cpp
return std::min(rb & 0x000001FF, 0x000000FFU) | ...
```

### ARGB32 混合

```cpp
static inline SkPMColor SkBlendARGB32(SkPMColor src, SkPMColor dst, U8CPU aa);
```

使用源 alpha 和额外的覆盖 alpha:
```cpp
src_scale = SkAlpha255To256(aa);
dst_scale = SkAlphaMulInv256(src.alpha, src_scale);
```

### 32位到16位转换

```cpp
static inline U16CPU SkPixel32ToPixel16(SkPMColor c);
static inline U16CPU SkPack888ToRGB16(U8CPU r, U8CPU g, U8CPU b);
```

宏版本(调试检查):
```cpp
#define SkR32ToR16(r)   SkR32ToR16_MACRO(r)  // 或内联函数(调试)
```

### 16位到32位转换

```cpp
static inline SkColor SkPixel16ToColor(U16CPU src);
```

### Lerp 操作

```cpp
static inline SkPMColor SkPMLerp(SkPMColor src, SkPMColor dst, unsigned scale);
```

别名到 `SkFastFourByteInterp256`。

## 内部实现细节

### 位操作优化

许多函数使用位操作而不是除法:
```cpp
(value * alpha256) >> 8  // 而不是 (value * alpha256) / 256
```

### 掩码常量

```cpp
static constexpr uint32_t kMask = 0x00FF00FF;
```

用于同时操作 R/B 或 A/G 通道。

### 平台差异

根据 CPU 架构选择不同实现:
```cpp
if (sizeof(void*) == 4) {
    return SkFastFourByteInterp256_32(...);  // 32位机器
} else {
    return SkFastFourByteInterp256_64(...);  // 64位机器
}
```

64 位机器上,64 位版本快约 10%。
32 位机器上,64 位版本慢约 40%。

### 饱和运算

某些混合操作需要饱和到 [0, 255]:
```cpp
std::min(rb & 0x000001FF, 0x000000FFU)  // 饱和到 0xFF
```

## 依赖关系

**依赖的模块:**

| 模块 | 用途 |
|------|------|
| `SkColor` | 基础颜色类型 |
| `SkColorPriv` | 更底层的颜色操作 |
| `SkAlphaType` | Alpha 类型定义 |
| `SkCPUTypes` | CPU 类型和字节序 |
| `SkTo` | 类型转换 |

**被依赖的模块:**

| 模块 | 关系 |
|------|------|
| 光栅化器 | 像素级绘制 |
| 混合器 | 混合模式实现 |
| 着色器 | 颜色生成 |
| 位图操作 | 像素格式转换 |
| 压缩纹理 | 颜色解压缩 |

## 设计模式与设计决策

### 内联函数

所有函数都是 `static inline`:
- 避免函数调用开销
- 允许编译器优化
- 适合性能关键路径

### 宏和内联的混合

调试模式使用内联函数(带断言),发布模式使用宏:
```cpp
#ifdef SK_DEBUG
    static inline unsigned SkR32ToR16(unsigned r) {
        SkR32Assert(r);
        return SkR32ToR16_MACRO(r);
    }
#else
    #define SkR32ToR16(r)   SkR32ToR16_MACRO(r)
#endif
```

### 分离和合并通道

Splay/Unsplay 技术允许同时操作多个通道:
- 减少指令数
- 利用 SIMD 可能性
- 避免通道间的依赖

### 定点运算

许多计算使用定点运算而不是浮点:
- 整数运算更快
- 避免浮点精度问题
- 适合像素级操作

## 性能考量

### SIMD 友好

许多函数的设计考虑了向量化:
- 使用位掩码同时操作多个通道
- 避免分支
- 数据布局有利于 SIMD

### 缓存友好

紧凑的数据表示:
- RGB565: 2 字节
- ARGB4444: 2 字节
- ARGB8888: 4 字节

### 无分支实现

大多数函数避免使用条件分支:
- 减少分支预测失败
- 适合流水线执行

### 自适应优化

根据平台选择最优实现:
- 32 位 vs 64 位机器
- 不同的混合算法

### 饱和处理

SrcOver 混合包含饱和处理,防止溢出:
```cpp
std::min(rb & 0x000001FF, 0x000000FFU)
```

虽然增加了成本,但保证正确性。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkColor.h` | 依赖 | 基础颜色类型 |
| `src/core/SkColorPriv.h` | 依赖 | 底层颜色操作 |
| `include/core/SkAlphaType.h` | 依赖 | Alpha 类型 |
| `include/private/base/SkCPUTypes.h` | 依赖 | 字节序定义 |
| `src/core/SkBlitter.h` | 使用者 | 混合器 |
| `src/core/SkSpriteBlitter.h` | 使用者 | 精灵混合 |
| `src/opts/` | 相关 | SIMD 优化版本 |
