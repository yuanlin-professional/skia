# SkColor

> 源文件: include/core/SkColor.h, src/core/SkColor.cpp

## 概述

`SkColor` 是 Skia 中颜色表示的核心模块,提供了全面的颜色处理功能。该模块定义了多种颜色类型(32 位整数颜色、浮点颜色)、颜色空间转换(RGB ↔ HSV)、预乘/非预乘转换,以及常用颜色常量。`SkColor` 使用未预乘的 ARGB 格式,组件顺序固定,而 `SkPMColor` 使用预乘格式,字节序依赖平台。

该模块还提供了模板化的 `SkRGBA4f` 浮点颜色结构,支持预乘和非预乘两种形式,并通过 SIMD 指令优化颜色转换操作。

## 架构位置

`SkColor` 在 Skia 架构中的位置:
- 位于公共 API 层(include/core),是基础数据类型
- 被 `SkPaint`、`SkCanvas`、`SkShader` 等绘图 API 广泛使用
- 为颜色空间转换提供基础功能
- 与 SIMD 优化模块(`src/base/SkVx.h`)集成
- 支持序列化/反序列化

## 主要类与结构体

### 基础类型定义

| 类型 | 定义 | 说明 |
|------|------|------|
| SkAlpha | uint8_t | Alpha 值,0=透明,255=不透明 |
| SkColor | uint32_t | 32 位 ARGB 颜色,未预乘,固定字节序 |
| SkPMColor | uint32_t | 32 位预乘颜色,字节序依赖平台 |

### SkRGBA4f 模板结构体

浮点颜色表示,支持预乘和非预乘两种形式。

**模板参数:**
- `kAT`: `SkAlphaType`,指定 `kPremul_SkAlphaType` 或 `kUnpremul_SkAlphaType`

**继承关系:**
- 无继承关系(POD 结构体)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fR | float | 红色分量,范围 [0, 1] |
| fG | float | 绿色分量,范围 [0, 1] |
| fB | float | 蓝色分量,范围 [0, 1] |
| fA | float | Alpha 分量,范围 [0, 1] |

### SkColor4f 别名

```cpp
using SkColor4f = SkRGBA4f<kUnpremul_SkAlphaType>;
```

未预乘的浮点颜色,Skia 公共 API 的标准浮点颜色类型。

### 预定义常量

#### 32 位颜色常量

| 常量 | 值 | ARGB |
|------|----|----|
| SK_ColorTRANSPARENT | 0x00000000 | (0,0,0,0) |
| SK_ColorBLACK | 0xFF000000 | (255,0,0,0) |
| SK_ColorWHITE | 0xFFFFFFFF | (255,255,255,255) |
| SK_ColorRED | 0xFFFF0000 | (255,255,0,0) |
| SK_ColorGREEN | 0xFF00FF00 | (255,0,255,0) |
| SK_ColorBLUE | 0xFF0000FF | (255,0,0,255) |
| SK_ColorYELLOW | 0xFFFFFF00 | (255,255,255,0) |
| SK_ColorCYAN | 0xFF00FFFF | (255,0,255,255) |
| SK_ColorMAGENTA | 0xFFFF00FF | (255,255,0,255) |

#### 浮点颜色常量(SkColors 命名空间)

```cpp
namespace SkColors {
    constexpr SkColor4f kBlack = {0, 0, 0, 1};
    constexpr SkColor4f kWhite = {1, 1, 1, 1};
    constexpr SkColor4f kRed = {1, 0, 0, 1};
    // ...
}
```

## 公共 API 函数

### 颜色构造与分解

```cpp
// 构造 SkColor
constexpr SkColor SkColorSetARGB(U8CPU a, U8CPU r, U8CPU g, U8CPU b)
#define SkColorSetRGB(r, g, b)  SkColorSetARGB(0xFF, r, g, b)

// 分解 SkColor
#define SkColorGetA(color)      (((color) >> 24) & 0xFF)
#define SkColorGetR(color)      (((color) >> 16) & 0xFF)
#define SkColorGetG(color)      (((color) >>  8) & 0xFF)
#define SkColorGetB(color)      (((color) >>  0) & 0xFF)

// 设置 Alpha
[[nodiscard]] constexpr SkColor SkColorSetA(SkColor c, U8CPU a)
```

### 预乘转换

```cpp
SK_API SkPMColor SkPreMultiplyARGB(U8CPU a, U8CPU r, U8CPU g, U8CPU b)
SK_API SkPMColor SkPreMultiplyColor(SkColor c)
```

将未预乘颜色转换为预乘格式:
```
R' = R * A / 255
G' = G * A / 255
B' = B * A / 255
```

### RGB ↔ HSV 转换

```cpp
SK_API void SkRGBToHSV(U8CPU red, U8CPU green, U8CPU blue, SkScalar hsv[3])
static inline void SkColorToHSV(SkColor color, SkScalar hsv[3])

SK_API SkColor SkHSVToColor(U8CPU alpha, const SkScalar hsv[3])
static inline SkColor SkHSVToColor(const SkScalar hsv[3])  // Alpha=255
```

HSV 分量:
- `hsv[0]`: Hue(色相),范围 [0, 360)
- `hsv[1]`: Saturation(饱和度),范围 [0, 1]
- `hsv[2]`: Value(明度),范围 [0, 1]

### SkRGBA4f 成员函数

```cpp
// 比较运算符
bool operator==(const SkRGBA4f& other) const
bool operator!=(const SkRGBA4f& other) const

// 算术运算符
SkRGBA4f operator*(float scale) const
SkRGBA4f operator*(const SkRGBA4f& scale) const

// 数组访问
const float* vec() const
float* vec()
std::array<float, 4> array() const
float operator[](int index) const
float& operator[](int index)

// 查询
bool isOpaque() const     // fA == 1.0f
bool fitsInBytes() const  // 所有分量在 [0, 1]

// 转换(依赖 kAT)
static SkRGBA4f FromColor(SkColor color)      // 仅 kUnpremul
SkColor toSkColor() const                     // 仅 kUnpremul
static SkRGBA4f FromPMColor(SkPMColor)        // 仅 kPremul
uint32_t toBytes_RGBA() const                 // RGBA 字节序
static SkRGBA4f FromBytes_RGBA(uint32_t color)

// 预乘/非预乘转换
SkRGBA4f<kPremul_SkAlphaType> premul() const    // kUnpremul → kPremul
SkRGBA4f<kUnpremul_SkAlphaType> unpremul() const  // kPremul → kUnpremul

// 辅助函数
SkRGBA4f makeOpaque() const           // 设置 fA = 1.0f
SkRGBA4f pinAlpha() const             // 将 fA 限制在 [0, 1]
SkRGBA4f withAlpha(float a) const     // 替换 alpha
```

## 内部实现细节

### SkColor 字节布局

```cpp
SkColor = (A << 24) | (R << 16) | (G << 8) | (B << 0)
```

固定的大端序布局,与平台无关。

### SkPMColor 平台相关布局

根据 `kN32_SkColorType` 的定义:
- 大多数平台:`SkColorType::kBGRA_8888` → BGRA 字节序
- 其他平台可能不同

### RGB → HSV 算法

```cpp
void SkRGBToHSV(U8CPU r, U8CPU g, U8CPU b, SkScalar hsv[3]) {
    unsigned min = std::min(r, std::min(g, b));
    unsigned max = std::max(r, std::max(g, b));
    unsigned delta = max - min;

    SkScalar v = ByteToScalar(max);

    if (delta == 0) {  // 灰度
        hsv[0] = 0;
        hsv[1] = 0;
        hsv[2] = v;
        return;
    }

    SkScalar s = ByteDivToScalar(delta, max);

    SkScalar h;
    if (r == max) {
        h = ByteDivToScalar(g - b, delta);
    } else if (g == max) {
        h = 2 + ByteDivToScalar(b - r, delta);
    } else {  // b == max
        h = 4 + ByteDivToScalar(r - g, delta);
    }

    h *= 60;
    if (h < 0) h += 360;

    hsv[0] = h;
    hsv[1] = s;
    hsv[2] = v;
}
```

### HSV → RGB 算法

```cpp
SkColor SkHSVToColor(U8CPU a, const SkScalar hsv[3]) {
    SkScalar s = SkTPin(hsv[1], 0.0f, 1.0f);
    SkScalar v = SkTPin(hsv[2], 0.0f, 1.0f);
    U8CPU v_byte = SkScalarRoundToInt(v * 255);

    if (SkScalarNearlyZero(s)) {  // 灰度
        return SkColorSetARGB(a, v_byte, v_byte, v_byte);
    }

    SkScalar hx = (hsv[0] < 0 || hsv[0] >= 360) ? 0 : hsv[0] / 60;
    SkScalar w = SkScalarFloorToScalar(hx);
    SkScalar f = hx - w;

    unsigned p = SkScalarRoundToInt((1 - s) * v * 255);
    unsigned q = SkScalarRoundToInt((1 - s * f) * v * 255);
    unsigned t = SkScalarRoundToInt((1 - s * (1 - f)) * v * 255);

    switch ((unsigned)w) {
        case 0: return SkColorSetARGB(a, v_byte, t, p);
        case 1: return SkColorSetARGB(a, q, v_byte, p);
        case 2: return SkColorSetARGB(a, p, v_byte, t);
        case 3: return SkColorSetARGB(a, p, q, v_byte);
        case 4: return SkColorSetARGB(a, t, p, v_byte);
        default: return SkColorSetARGB(a, v_byte, p, q);
    }
}
```

### SIMD 优化的颜色转换

```cpp
template <>
SkColor4f SkColor4f::FromColor(SkColor bgra) {
    SkColor4f rgba;
    swizzle_rb(Sk4f_fromL32(bgra)).store(rgba.vec());
    return rgba;
}
```

使用 `src/base/SkVx.h` 的 SIMD 向量:
- `Sk4f_fromL32`: 将 32 位整数转为 4 个浮点数(0-255 → 0-1)
- `swizzle_rb`: 交换红蓝通道(BGRA → RGBA)
- 利用 SSE/NEON 指令加速

```cpp
template <>
SkColor SkColor4f::toSkColor() const {
    return Sk4f_toL32(swizzle_rb(skvx::float4::Load(this->vec())));
}
```

反向转换:
- 加载浮点向量
- 交换红蓝通道
- 转为 32 位整数(0-1 → 0-255)

### 预乘/非预乘转换

```cpp
SkRGBA4f<kPremul_SkAlphaType> premul() const {
    static_assert(kAT == kUnpremul_SkAlphaType, "");
    return { fR * fA, fG * fA, fB * fA, fA };
}

SkRGBA4f<kUnpremul_SkAlphaType> unpremul() const {
    static_assert(kAT == kPremul_SkAlphaType, "");

    if (fA == 0.0f) {
        return { 0, 0, 0, 0 };
    } else {
        float invAlpha = 1 / fA;
        return { fR * invAlpha, fG * invAlpha, fB * invAlpha, fA };
    }
}
```

编译期检查确保只能在正确的类型上调用。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkAlphaType.h | Alpha 类型枚举 |
| include/core/SkScalar.h | 浮点类型定义 |
| include/private/base/SkCPUTypes.h | CPU 类型定义 |
| include/private/base/SkTPin.h | 数值钳位 |
| src/base/SkVx.h | SIMD 向量运算 |
| src/core/SkColorData.h | 颜色数据内部定义 |
| src/core/SkSwizzlePriv.h | 通道交换 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkPaint | 设置颜色 |
| SkCanvas | 清除颜色,背景色 |
| SkShader | 颜色着色器 |
| SkColorFilter | 颜色滤镜 |
| SkImageInfo | 颜色类型 |
| 几乎所有绘图 API | 颜色参数 |

## 设计模式与设计决策

### 类型安全的预乘标记

```cpp
template <SkAlphaType kAT>
struct SkRGBA4f { ... };
```

使用模板参数而非运行时标志:
- 编译期类型检查
- 避免运行时错误
- 零运行时开销
- API 更清晰(类型即文档)

### 固定字节序 vs 平台相关

- `SkColor`: 固定 ARGB 字节序,跨平台一致,用于 API
- `SkPMColor`: 平台相关字节序,匹配 `kN32_SkColorType`,用于位图

设计理由:
- API 稳定性和可移植性
- 位图格式与硬件匹配,提高性能

### 值语义

颜色类型均为值类型:
- 小对象(4-16 字节)
- 可内联
- 无动态分配
- 线程安全

### 命名空间组织

```cpp
namespace SkColors {
    constexpr SkColor4f kRed = {1, 0, 0, 1};
    // ...
}
```

浮点常量使用命名空间,避免与宏常量冲突。

## 性能考量

### SIMD 加速

```cpp
swizzle_rb(Sk4f_fromL32(bgra))
```

利用 SIMD 指令并行处理 4 个颜色分量:
- SSE2/AVX(x86): 单指令处理
- NEON(ARM): 向量化加载/存储
- 相比标量代码提速 2-4 倍

### 内联小函数

```cpp
static constexpr inline SkColor SkColorSetARGB(U8CPU a, U8CPU r, U8CPU g, U8CPU b) {
    return (a << 24) | (r << 16) | (g << 8) | (b << 0);
}
```

`constexpr` + `inline`:
- 编译期求值(如果参数是常量)
- 无函数调用开销
- 寄存器操作,极快

### 宏 vs 函数

颜色分解使用宏:
```cpp
#define SkColorGetR(color)  (((color) >> 16) & 0xFF)
```

优势:
- 零开销
- 编译器容易优化
- 避免函数调用

### 预乘优化

```cpp
SkPMColor SkPreMultiplyARGB(U8CPU a, U8CPU r, U8CPU g, U8CPU b) {
    return SkPremultiplyARGBInline(a, r, g, b);
}
```

`SkPremultiplyARGBInline` 可能使用查表或 SIMD,比朴素乘法快。

### HSV 转换优化

使用整数算术代替浮点:
```cpp
unsigned p = SkScalarRoundToInt((1 - s) * v * 255);
```

只在必要时使用浮点,最终计算使用整数舍入。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkPaint.h | 使用者 | 设置绘制颜色 |
| include/core/SkShader.h | 使用者 | 颜色着色器 |
| include/core/SkImageInfo.h | 相关 | 颜色类型和空间 |
| src/core/SkColorData.h | 内部实现 | 颜色数据布局 |
| src/core/SkSwizzlePriv.h | 内部实现 | 通道交换 |
| src/base/SkVx.h | SIMD 支持 | 向量运算 |
| include/private/chromium/SkPMColor.h | 扩展 | SkPMColor 函数 |
| tests/ColorTest.cpp | 测试 | 颜色功能测试 |
