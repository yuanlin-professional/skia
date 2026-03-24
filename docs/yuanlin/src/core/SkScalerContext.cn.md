# SkScalerContext

> 源文件: src/core/SkScalerContext.h, src/core/SkScalerContext.cpp

## 概述

`SkScalerContext` 是 Skia 字体渲染系统的核心抽象类,负责将字体轮廓(glyphs)转换为可渲染的位图或路径。它封装了字体光栅化的所有参数,包括字体大小、变换矩阵、提示(hinting)设置、抗锯齿模式等,并提供统一接口来生成字形的度量信息、图像数据和路径数据。该类是字体渲染管线中字体文件与最终渲染输出之间的桥梁。

## 架构位置

`SkScalerContext` 位于 Skia 的 `src/core` 核心模块,处于字体渲染架构的中间层:

- **上层**: `SkFont`、`SkPaint`、`SkTypeface` 提供用户级字体配置
- **中间层**: `SkScalerContext` 执行字形光栅化和度量计算
- **下层**: 平台特定的字体引擎(FreeType、CoreText、DirectWrite)实现具体渲染
- **相关系统**: 与 `SkGlyph`(字形数据)、`SkStrike`(字形缓存)、`SkMask`(位图格式)紧密协作

## 主要类与结构体

### SkScalerContextRec

| 属性 | 说明 |
|------|------|
| **继承关系** | 独立结构体(必须是紧密打包的,用于校验和计算) |
| **关键成员变量** | `fTypefaceID`: 字体ID<br>`fTextSize/fPreScaleX/fPreSkewX`: 文本变换参数<br>`fPost2x2[2][2]`: 设备矩阵<br>`fFrameWidth/fMiterLimit`: 描边参数<br>`fMaskFormat`: 遮罩格式<br>`fFlags`: 渲染标志位<br>`fForegroundColor`: 前景色(用于彩色字体)<br>`fLumBits/fDeviceGamma/fContrast`: 预混合参数 |

存储字形渲染所需的所有配置参数,用作字形缓存的键。

### SkScalerContextEffects

| 属性 | 说明 |
|------|------|
| **继承关系** | 独立结构体 |
| **关键成员变量** | `fPathEffect`: 路径效果<br>`fMaskFilter`: 遮罩滤镜 |

封装影响字形外观的特效对象。

### SkScalerContext

| 属性 | 说明 |
|------|------|
| **继承关系** | 抽象基类(需要平台实现子类化) |
| **关键成员变量** | `fRec`: 渲染配置记录<br>`fTypeface`: 字体引用<br>`fPathEffect/fMaskFilter`: 效果对象<br>`fGenerateImageFromPath`: 是否从路径生成图像<br>`fPreBlend`: 预混合查找表 |

字形光栅化上下文的抽象基类,定义渲染接口和公共实现。

## 公共 API 函数

### SkScalerContextRec 核心方法

```cpp
// 矩阵计算
SkMatrix getMatrixFrom2x2() const;           // 从2x2数组构建矩阵
SkMatrix getLocalMatrix() const;             // 获取局部文本矩阵
SkMatrix getSingleMatrix() const;            // 获取组合矩阵

// 分解变换矩阵为缩放和剩余部分
bool computeMatrices(PreMatrixScale preMatrixScale,
                     SkVector* scale, SkMatrix* remaining,
                     SkMatrix* remainingWithoutRotation = nullptr,
                     SkMatrix* remainingRotation = nullptr,
                     SkMatrix* total = nullptr) const;

// Gamma和对比度设置
void setDeviceGamma(SkScalar g);             // 设置设备伽马值
void setContrast(SkScalar c);                // 设置对比度
void ignoreGamma();                          // 忽略伽马校正
void ignorePreBlend();                       // 忽略预混合

// 颜色设置
void setLuminanceColor(SkColor c);           // 设置亮度颜色
SkColor getLuminanceColor() const;           // 获取亮度颜色
```

### SkScalerContext 核心方法

```cpp
// 字形生成主接口
SkGlyph makeGlyph(SkPackedGlyphID, SkArenaAlloc*);  // 创建字形(度量信息)
void getImage(const SkGlyph&);                      // 生成字形位图
void getPath(SkGlyph&, SkArenaAlloc*);             // 生成字形路径
sk_sp<SkDrawable> getDrawable(SkGlyph&);           // 获取可绘制对象
void getFontMetrics(SkFontMetrics*);               // 获取字体度量

// 静态工厂方法
static void MakeRecAndEffects(const SkFont&, const SkPaint&,
                              const SkSurfaceProps&,
                              SkScalerContextFlags,
                              const SkMatrix& deviceMatrix,
                              SkScalerContextRec* rec,
                              SkScalerContextEffects* effects);

// 描述符管理
static SkDescriptor* AutoDescriptorGivenRecAndEffects(
    const SkScalerContextRec& rec,
    const SkScalerContextEffects& effects,
    SkAutoDescriptor* ad);

// Gamma查找表
static size_t GetGammaLUTSize(SkScalar contrast, SkScalar gamma,
                              int* width, int* height);
static bool GetGammaLUTData(SkScalar contrast, SkScalar gamma,
                            uint8_t* data);
```

## 内部实现细节

### 字形生成流程

1. **度量生成**: `internalMakeGlyph` → `generateMetrics` (子类实现) → 计算边界框和前进值
2. **路径处理**: 应用 `PathEffect` 和描边参数,可能从路径生成度量
3. **遮罩过滤**: 应用 `MaskFilter` 调整最终边界
4. **图像生成**: `getImage` → `generateImage` (子类实现) 或 `generateImageFromPath`
5. **路径生成**: `getPath` → `generatePath` (子类实现) → 应用子像素偏移和变换

### LCD 文本渲染

使用 FIR(有限冲激响应)滤波器进行子像素渲染:
- 将 A8 图像放大 4 倍采样
- 应用 RGB 三通道滤波器(红色和蓝色偏移,绿色居中)
- 使用高斯系数实现平滑抗锯齿
- 支持垂直和水平 LCD 布局,BGR/RGB 像素顺序

### 遮罩过滤器集成

`fMaskFilter` 处理流程:
1. 生成未过滤的字形图像到临时缓冲区
2. 调用 `filterMask` 生成过滤后的遮罩
3. 计算源遮罩和目标遮罩的交集
4. 将过滤结果复制到最终字形缓冲区

### 矩阵分解算法

`computeMatrices` 使用 QR 分解(通过 Givens 旋转):
- 将总矩阵 A 分解为 A = G^(-1) * GA,其中 G 是旋转,GA 是无旋转缩放
- 提取缩放因子 s(全缩放/仅垂直/整数垂直)
- 计算剩余变换 sA = A / s
- 处理奇异矩阵和近零缩放因子

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkTypeface | 提供字体数据和字形访问 |
| SkGlyph | 存储字形度量和图像数据 |
| SkMask/SkMaskBuilder | 位图遮罩格式和操作 |
| SkMaskGamma | Gamma 校正和预混合查找表 |
| SkPathEffect | 路径效果(如虚线) |
| SkMaskFilter | 遮罩滤镜(如模糊) |
| SkDescriptor | 缓存键生成和参数序列化 |
| SkArenaAlloc | 字形数据内存分配 |
| SkDraw/SkRasterClip | 路径光栅化 |
| SkFont/SkPaint | 文本样式和绘制参数 |

### 被依赖的模块

| 模块 | 依赖方式 |
|------|----------|
| SkStrike | 使用 `SkScalerContext` 生成和缓存字形 |
| SkGlyphRunPainter | 通过 Strike 间接使用进行文本绘制 |
| 平台字体引擎 | FreeType/CoreText/DirectWrite 子类化实现 |
| SkRemoteGlyphCache | 远程字形缓存使用序列化的 Rec |

## 设计模式与设计决策

### 抽象工厂模式

`SkTypeface` 负责创建平台特定的 `SkScalerContext` 子类,实现平台无关的接口。

### 不可变配置对象

`SkScalerContextRec` 作为不可变的配置对象:
- 用作缓存键(通过校验和)
- 必须是紧密打包的结构(SK_BEGIN_REQUIRE_DENSE)
- 所有字节必须初始化以保证哈希一致性

### 延迟计算策略

字形数据按需生成:
- 度量信息首先计算(用于布局)
- 图像和路径仅在实际需要时生成
- 使用 `SkArenaAlloc` 管理临时数据生命周期

### Gamma 校正优化

使用全局缓存的 `SkMaskGamma` 对象:
- 通过静态变量缓存常用的 gamma 查找表
- 互斥锁保护并发访问
- 线性 gamma 和默认 gamma 使用单例

### 路径优先渲染

当设置了 `fPathEffect` 或需要描边时,通过 `fGenerateImageFromPath` 标志强制从路径生成图像,确保效果正确应用。

## 性能考量

### LCD 文本尺寸限制

定义 `SK_MAX_SIZE_FOR_LCDTEXT`(默认 48):
- 超过此尺寸时降级为 A8 抗锯齿
- 减少大字号时的内存消耗和渲染时间
- 大尺寸时 LCD 渲染质量提升不明显

### Gamma 查找表缓存

预计算的 gamma 查找表避免每像素计算:
- 3x3x3 位深度平衡精度和缓存大小
- 全局共享减少内存占用
- 仅对非线性 gamma 构建查找表

### 子像素定位优化

`kSubpixelPositioning_Flag` 允许 1/4 像素精度:
- 提高小字号渲染质量
- 路径偏移在 `internalGetPath` 中应用
- 使用定点数避免浮点运算

### 矩阵松弛化

`sk_relax` 函数将矩阵值量化到 1/1024 精度:
- 合并微小差异的矩阵到同一缓存条目
- 减少缓存未命中率
- 对视觉质量影响可忽略

### 遮罩过滤器内存管理

智能复用原始字形缓冲区:
- 如果格式和大小匹配,直接使用原始缓冲区
- 仅在必要时分配临时存储
- 避免不必要的内存拷贝

## 相关文件

| 文件 | 关系 |
|------|------|
| src/core/SkGlyph.h/cpp | 字形数据结构 |
| src/core/SkStrike.h/cpp | 字形缓存管理 |
| src/core/SkMaskGamma.h/cpp | Gamma 校正实现 |
| src/core/SkDescriptor.h/cpp | 缓存键序列化 |
| src/core/SkFont.h | 字体配置 API |
| src/core/SkPaint.h | 绘制样式配置 |
| include/core/SkTypeface.h | 字体文件抽象 |
| src/ports/SkScalerContext_*.cpp | 平台特定实现 |
| src/core/SkDraw.cpp | 路径光栅化 |
| src/core/SkMaskFilterBase.h | 遮罩滤镜接口 |
