# PaintParams

> 源文件
> - src/gpu/graphite/PaintParams.h
> - src/gpu/graphite/PaintParams.cpp

## 概述

`PaintParams` 是 Skia Graphite 渲染引擎中表示绘制着色状态的类，从 `SkPaint` 中提取并封装了着色器、颜色滤镜、混合模式等着色相关参数。它专注于着色状态，不包括样式（如描边宽度）和复杂效果（如遮罩滤镜、图像滤镜、路径效果）。

`ShadingParams` 在 `PaintParams` 的基础上增加了每像素的裁剪和抗锯齿状态，以及根据硬件能力确定的最终混合实现方式，是生成 `UniquePaintParamsID` 和提取 uniform/纹理数据的聚合参数。

这两个类都是短生命周期对象，用于处理绘制效果并转换为着色器键和数据，在绘制调用结束时即失效，不保持高级 Skia 对象的生命周期。

## 架构位置

```
SkPaint (Skia 公共 API)
  └── PaintParams (着色状态提取)
      └── ShadingParams (加上裁剪/抗锯齿/混合)
          └── UniquePaintParamsID (着色器键)
```

`PaintParams` 位于 Skia 公共 API 和 Graphite 着色器系统之间的适配层。

## 主要类与结构体

### SimpleImage

```cpp
struct SimpleImage {
    const SkImage* fImage;
    const SkMatrix* fLocalMatrix = nullptr;
    SkRect fSubset;
    SkSamplingOptions fSamplingOptions;
};
```

**用途**：存储隐式图像着色器的参数（如 `drawImageRect`）

**优势**：避免创建 `SkImageShader` 对象和矩阵求逆的开销

**语义**：
- `fSubset`：后局部矩阵的严格裁剪矩形（相对于图像纹素）
- 假设 clamp 平铺模式

### PaintParams

**核心职责**：
- 从 `SkPaint` 提取着色状态
- 支持原始混合器（如顶点或文本颜色）
- 处理图像着色器覆盖

**关键成员**：

```cpp
SkColor4f fColor;
std::pair<const SkBlender*, SkBlendMode> fFinalBlend;
const SkShader* fShader;
const SimpleImage* fImageShader;      // 覆盖 fShader（颜色图像），混合（alpha 图像）
const SkColorFilter* fColorFilter;
const SkBlender* fPrimitiveBlender;   // nullptr 表示跳过原始色混合
bool fSkipColorXform;
bool fDither;
```

### ShadingParams

**核心职责**：
- 聚合 `PaintParams`、裁剪、覆盖率、目标格式
- 确定是否需要 dst read
- 生成着色器键

**关键成员**：

```cpp
const PaintParams& fPaint;
const NonMSAAClip& fNonMSAAClip;
const SkShader* fClipShader;
const SkEnumBitMask<DstUsage> fDstUsage;  // Dst 读取需求
```

## 公共 API 函数

### PaintParams 构造函数

#### 从 SkPaint 构造

```cpp
explicit PaintParams(const SkPaint& paint,
                     const SkBlender* primitiveBlender = nullptr,
                     bool skipColorXform = false,
                     bool ignoreShader = false);
```

**参数**：
- `paint`：源 SkPaint 对象
- `primitiveBlender`：原始色混合器（如 drawVertices 的顶点颜色）
- `skipColorXform`：跳过原始色的色彩空间转换
- `ignoreShader`：忽略 paint 的着色器

**原始混合语义**：
```
原始色 (src)  blend  paint 颜色/着色器 (dst)
```

#### 带图像覆盖

```cpp
PaintParams(const SkPaint& paint,
            const SimpleImage& imageOverride,
            float xtraAlpha = 1.f);
```

**用途**：处理 `drawImageRect` 等隐式图像着色器

**行为**：
- `xtraAlpha` 与 paint 的 alpha 相乘
- `imageOverride` 覆盖或混合 paint 的着色器

#### 纯颜色构造

```cpp
PaintParams(const SkColor4f& color, SkBlendMode finalBlendMode);
```

**用途**：创建常量颜色的 PaintParams

### 访问器方法

```cpp
const SkColor4f& color() const;
const SkShader* shader() const;
const SimpleImage* imageShader() const;
const SkColorFilter* colorFilter() const;
const SkBlender* primitiveBlender() const;
bool skipPrimitiveColorXform() const;
const SkBlender* finalBlender() const;
SkBlendMode finalBlendMode() const;
bool dither() const;
```

### 色彩空间转换

```cpp
static SkColor4f Color4fPrepForDst(SkColor4f srgb, const SkColorInfo& dstColorInfo);
```

**功能**：将 sRGB 颜色转换到目标色彩空间

## ShadingParams API

### 构造函数

```cpp
ShadingParams(const Caps* caps,
              const PaintParams& paint,
              const NonMSAAClip& nonMSAAClip,
              const SkShader* clipShader,
              Coverage coverage,
              TextureFormat targetFormat);
```

**参数**：
- `caps`：设备能力
- `paint`：绘制参数
- `nonMSAAClip`：非 MSAA 裁剪（解析或图集）
- `clipShader`：裁剪着色器
- `coverage`：渲染步骤的覆盖率类型
- `targetFormat`：目标纹理格式

### toKey

```cpp
using Result = std::tuple<UniquePaintParamsID, SkEnumBitMask<DstUsage>>;
std::optional<Result> toKey(const KeyContext&) const;
```

**功能**：生成着色器键并返回 dst 使用标志

**返回值**：
- `UniquePaintParamsID`：着色器唯一标识符
- `DstUsage`：dst 读取/混合需求
- `std::nullopt`：键生成失败

### dstReadRequired

```cpp
bool dstReadRequired() const;
```

**功能**：检查是否需要读取目标颜色

## 内部实现细节

### 最终混合表示

```cpp
std::pair<const SkBlender*, SkBlendMode> fFinalBlend;
```

**编码规则**：
- 如果 `fFinalBlend.first` 非空：使用运行时混合器（`SkBlender`）
- 否则：使用 `fFinalBlend.second` 的混合模式

**硬件混合优化**：
- 当使用着色器混合时，HW 混合配置设为 `kSrc`

### 图像着色器覆盖

`fImageShader` 的优先级高于 `fShader`：

```cpp
if (fImageShader) {
    if (isAlphaOnly(fImageShader->fImage)) {
        // Alpha 图像：与 fShader 混合
    } else {
        // 颜色图像：完全覆盖 fShader
    }
}
```

### ShadingParams 键生成流程

`toKey` 方法的处理顺序：

1. **addPaintColorToKey**：添加 paint 颜色（如果需要）
2. **handlePrimitiveColor**：处理原始色混合
3. **handlePaintAlpha**：处理 paint 的 alpha
4. **handleColorFilter**：添加颜色滤镜
5. **handleDithering**：添加抖动
6. **handleDstRead**：处理 dst 读取需求
7. **handleClipping**：添加裁剪

**每步都可能失败**：返回 `std::nullopt`

### Dst Read 策略

根据混合模式和覆盖率确定 dst 读取需求：

```cpp
if (blendRequiresDst(finalBlendMode)) {
    if (coverage == Coverage::kNone) {
        // 完全覆盖，可能使用 HW 混合
        fDstUsage = DstUsage::kBlendRequired;
    } else {
        // 部分覆盖，必须读取 dst
        fDstUsage = DstUsage::kDstReadRequired;
    }
}
```

### 原始色混合处理

```cpp
bool handlePrimitiveColor(const KeyContext& keyContext) const {
    if (fPaint.primitiveBlender()) {
        // 原始色作为 src，paint 颜色/着色器作为 dst
        AddToKey(keyContext, fPaint.primitiveBlender());
        return true;
    }
    return false; // 跳过，直接使用 paint 着色
}
```

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `SkPaint` | 源绘制参数 |
| `SkShader` | 着色器 |
| `SkColorFilter` | 颜色滤镜 |
| `SkBlender` | 混合器 |
| `NonMSAAClip` | 裁剪信息 |
| `Caps` | 设备能力 |

### 工具类

| 类型 | 用途 |
|------|------|
| `KeyContext` | 键生成上下文 |
| `PaintParamsKeyBuilder` | 键构建器 |
| `UniquePaintParamsID` | 着色器唯一标识 |

## 设计模式与设计决策

### 1. 适配器模式

`PaintParams` 将 `SkPaint` 适配到 Graphite 的着色系统。

### 2. 策略模式

根据硬件能力和混合模式选择不同的混合策略：
- HW 混合
- 着色器混合
- Dst read

### 3. 值语义

`PaintParams` 和 `ShadingParams` 是值类型，通过引用传递源对象（如 `SkPaint*`、`NonMSAAClip&`），不持有所有权。

### 4. 不可变性

构造后不可修改，确保线程安全和键生成的一致性。

### 5. 分层设计

- **PaintParams**：纯着色状态
- **ShadingParams**：着色 + 裁剪 + 抗锯齿 + 硬件适配

### 6. 优化路径

`SimpleImage` 避免创建临时 `SkImageShader` 对象，直接编码图像参数。

## 性能考量

### 避免对象分配

1. **SimpleImage**：避免 `SkImageShader::MakeSubset` 的开销
2. **值类型**：栈上分配，无堆分配
3. **引用传递**：不拷贝 `SkPaint` 等大对象

### 色彩空间转换缓存

`Color4fPrepForDst` 可能被多次调用，但转换步骤由 `SkColorSpaceXformSteps` 优化。

### 键生成优化

1. **早期退出**：每个处理步骤失败时立即返回
2. **条件跳过**：不需要的步骤完全跳过（如无 colorFilter）
3. **内联小函数**：访问器方法易于内联

### 抖动检测

仅在必要时添加抖动块：

```cpp
if (fPaint.dither() && needsDithering(targetFormat)) {
    AddDitherBlock(keyContext, targetFormat);
}
```

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `include/core/SkPaint.h` | Skia 绘制参数 |
| `include/core/SkShader.h` | 着色器 |
| `include/core/SkColorFilter.h` | 颜色滤镜 |
| `include/core/SkBlendMode.h` | 混合模式 |
| `src/gpu/graphite/KeyContext.h` | 键生成上下文 |
| `src/gpu/graphite/KeyHelpers.h` | 键生成辅助函数 |
| `src/gpu/graphite/geom/NonMSAAClip.h` | 非 MSAA 裁剪 |
| `src/gpu/graphite/Renderer.h` | 渲染器（定义 Coverage） |
| `src/gpu/graphite/Caps.h` | 设备能力 |
