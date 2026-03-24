# GrColor

> 源文件
> - src/gpu/ganesh/GrColor.h

## 概述

`GrColor.h` 是 Ganesh GPU 后端中定义颜色表示和操作的核心头文件。它定义了 `GrColor` 类型（32 位整数颜色）及相关的宏和函数，用于在 GPU 渲染管线中高效地处理颜色数据。

该文件的主要内容包括：
- `GrColor` 类型定义（4 字节 RGBA 打包格式）
- 颜色分量打包和解包的宏
- 颜色标准化和转换函数
- 与 OpenGL ES 兼容的颜色通道顺序
- 颜色格式检测和转换工具

这些工具是 GPU 渲染中颜色处理的基础，确保颜色数据在 CPU 和 GPU 之间、不同着色器阶段之间正确传递。

## 架构位置

在 Skia 的 Ganesh GPU 渲染架构中，`GrColor` 位于底层工具层：

```
GPU 渲染管线
    ├── 顶点属性 (使用 GrColor)
    ├── Uniform 数据 (使用 GrColor)
    ├── 片段处理器 (使用 SkPMColor4f)
    └── GrColor 工具 (颜色转换和打包)
```

该文件提供的类型和函数被整个 Ganesh 后端使用，是颜色表示的基础抽象。

## 主要类与结构体

### GrColor 类型

```cpp
typedef uint32_t GrColor;
```

`GrColor` 是一个 32 位无符号整数，按特定顺序存储 RGBA 四个分量，每个分量占 8 位。

**内存布局（取决于字节序）：**

小端系统（x86/x64）：
```
位:     [31-24] [23-16] [15-8] [7-0]
分量:    A       B       G      R
```

大端系统（某些 ARM、PowerPC）：
```
位:     [31-24] [23-16] [15-8] [7-0]
分量:    R       G       B      A
```

这种设计确保与 OpenGL ES 的顶点属性顺序兼容，避免在着色器中进行分量交换。

## 公共 API 函数

### 颜色打包

```cpp
static inline GrColor GrColorPackRGBA(unsigned r, unsigned g, unsigned b, unsigned a);
```

**功能：** 将四个颜色分量打包成一个 `GrColor` 值。

**参数：**
- `r`, `g`, `b`, `a`: 颜色分量，取值范围 [0, 255]

**实现：**
```cpp
return  (r << GrColor_SHIFT_R) |
        (g << GrColor_SHIFT_G) |
        (b << GrColor_SHIFT_B) |
        (a << GrColor_SHIFT_A);
```

包含断言检查确保输入值在有效范围内。

### 颜色解包宏

```cpp
#define GrColorUnpackR(color)   (((color) >> GrColor_SHIFT_R) & 0xFF)
#define GrColorUnpackG(color)   (((color) >> GrColor_SHIFT_G) & 0xFF)
#define GrColorUnpackB(color)   (((color) >> GrColor_SHIFT_B) & 0xFF)
#define GrColorUnpackA(color)   (((color) >> GrColor_SHIFT_A) & 0xFF)
```

**功能：** 从 `GrColor` 中提取单个颜色分量。

**返回值：** 8 位颜色分量值 [0, 255]。

### 颜色标准化

```cpp
static inline float GrNormalizeByteToFloat(uint8_t value);
```

**功能：** 将 8 位颜色分量归一化到 [0.0, 1.0] 范围。

**实现：**
```cpp
static const float ONE_OVER_255 = 1.f / 255.f;
return value * ONE_OVER_255;
```

这是 GPU 着色器中常用的转换，因为着色器通常使用浮点数表示颜色。

### 颜色格式检测

```cpp
static inline bool SkPMColor4fFitsInBytes(const SkPMColor4f& color);
```

**功能：** 检测 `SkPMColor4f`（浮点颜色）是否可以无损表示为字节格式。

**用途：** 用于选择顶点属性类型。如果颜色适合字节格式，可以使用更紧凑的顶点数据，节省内存和带宽。

**实现：**
```cpp
return color.fitsInBytes();
```

内部检查颜色分量是否在 [0, 1] 范围内（对于预乘颜色，还要检查是否满足 RGB ≤ A）。

### 半精度浮点转换

```cpp
static inline uint64_t SkPMColor4f_toFP16(const SkPMColor4f& color);
```

**功能：** 将 `SkPMColor4f` 转换为半精度浮点格式（FP16）。

**返回值：** 64 位整数，包含四个 16 位半精度浮点分量。

**实现：**
```cpp
uint64_t halfColor;
to_half(skvx::float4::Load(color.vec())).store(&halfColor);
return halfColor;
```

使用 SIMD 指令（通过 `skvx`）进行高效的 FP32 到 FP16 转换。

## 内部实现细节

### 字节序相关的移位定义

```cpp
#ifdef SK_CPU_BENDIAN
    #define GrColor_SHIFT_R     24
    #define GrColor_SHIFT_G     16
    #define GrColor_SHIFT_B     8
    #define GrColor_SHIFT_A     0
#else
    #define GrColor_SHIFT_R     0
    #define GrColor_SHIFT_G     8
    #define GrColor_SHIFT_B     16
    #define GrColor_SHIFT_A     24
#endif
```

这些宏根据 CPU 字节序定义颜色分量的位移，确保颜色在内存中的布局与 OpenGL ES 的期望一致。

### 非法颜色值

```cpp
#define GrColor_ILLEGAL     (~(0xFF << GrColor_SHIFT_A))
```

**功能：** 定义一个特殊的"非法"颜色值，用于标记未初始化或无效的颜色。

**值：** RGB = 255, A = 0，这在预乘颜色中是非法的（因为预乘要求 RGB ≤ A）。

### OpenGL ES 兼容性

注释中解释了颜色分量顺序的设计决策：

```cpp
// ES doesn't allow BGRA vertex attrib order so if they were not in this order
// we'd have to swizzle in shaders.
```

OpenGL ES 不支持 BGRA 顶点属性顺序，因此必须使用 RGBA 顺序，否则需要在着色器中进行分量交换（swizzle），这会增加性能开销。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkColor` | Skia 核心颜色类型 |
| `GrTypes` | GPU 类型定义 |
| `SkHalf` | 半精度浮点数工具 |
| `SkVx` | SIMD 向量运算 |
| `SkColorData` | 颜色数据定义 |
| `SkColorPriv` | 颜色私有工具 |
| `BufferWriter` | 缓冲区写入工具 |

### 被依赖的模块

`GrColor` 被广泛使用于：

| 模块 | 使用方式 |
|------|---------|
| `GrVertexWriter` | 写入顶点颜色属性 |
| `GrGeometryProcessor` | 处理顶点颜色输入 |
| `GrOp` | 绘制操作中的颜色参数 |
| `GrPaint` | 绘制时的颜色信息 |
| 各种几何生成器 | 生成带颜色的顶点数据 |

## 设计模式与设计决策

### 类型别名

使用 `typedef` 定义 `GrColor` 为 `uint32_t`，而非定义新类。这是一种轻量级抽象，避免了类定义的开销，同时提供了语义清晰的类型名称。

### 宏 vs 内联函数

颜色解包使用宏而非内联函数：
- **优点**：零开销抽象，编译器可以更好地优化
- **缺点**：类型安全性较差，调试更困难

颜色打包使用内联函数：
- **优点**：类型检查，更安全的参数验证
- **缺点**：可能略微增加编译时间

### 字节序抽象

通过条件编译处理字节序差异，确保代码在不同平台上正确工作。这是跨平台代码的常见模式。

### 性能优先

整个设计以性能为优先：
- 使用整数运算而非浮点（更快）
- 使用位运算进行打包/解包（编译器可以优化为单条指令）
- 使用 SIMD 进行批量转换

### 与硬件对齐

颜色顺序设计考虑了 GPU 硬件的要求（OpenGL ES 兼容性），避免运行时的数据重排。

## 性能考量

### 位运算效率

颜色打包和解包使用位移和掩码操作，这些操作在现代 CPU 上通常编译为单条指令，非常高效。

### SIMD 优化

`SkPMColor4f_toFP16` 使用 SIMD 指令（通过 `skvx`），可以并行转换四个分量，相比标量代码快 4 倍。

### 内存布局

`GrColor` 是 4 字节对齐的，可以高效地加载和存储。在顶点缓冲区中，紧凑的表示减少了内存带宽消耗。

### 常量优化

`GrNormalizeByteToFloat` 使用预计算的常量 `ONE_OVER_255`，避免每次调用时的除法运算。

### 类型选择

`SkPMColor4fFitsInBytes` 允许根据颜色范围动态选择顶点属性类型：
- 字节格式：4 字节/顶点
- 浮点格式：16 字节/顶点
- 半精度格式：8 字节/顶点

选择合适的格式可以显著减少内存使用和带宽消耗。

### 预乘 Alpha 约定

虽然文件本身不强制预乘，但注释提到预乘约定（RGB ≤ A）。预乘颜色在混合操作中更高效，是 GPU 渲染的标准做法。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkColor.h` | 依赖 | Skia 核心颜色定义 |
| `include/gpu/ganesh/GrTypes.h` | 依赖 | GPU 类型定义 |
| `src/base/SkHalf.h` | 依赖 | 半精度浮点工具 |
| `src/base/SkVx.h` | 依赖 | SIMD 向量运算 |
| `src/core/SkColorData.h` | 依赖 | 颜色数据类型 |
| `src/gpu/BufferWriter.h` | 依赖 | 缓冲区写入工具 |
| `src/gpu/ganesh/GrVertexWriter.h` | 使用者 | 顶点数据写入 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 使用者 | 几何处理器 |
| `src/gpu/ganesh/GrPaint.h` | 使用者 | 绘制颜色 |
