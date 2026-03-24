# SkPaint

> 源文件: include/core/SkPaint.h, src/core/SkPaint.cpp

## 概述

`SkPaint` 是 Skia 中最核心的绘图属性类，封装了所有与绘制外观相关的设置。它控制着绘制时的颜色、样式、效果和变换，是 Skia 绘图 API 的基础组件之一。`SkPaint` 采集了 `SkCanvas` 裁剪和矩阵之外的所有绘图选项，包括描边属性、抗锯齿、颜色滤镜、着色器、混合模式等。

该类的设计理念是将样式与几何分离，同一个 `SkPaint` 对象可以应用于不同的绘图操作（绘制矩形、路径、文本等），提供统一的外观控制。

## 架构位置

`SkPaint` 位于 Skia 公共 API 的核心层：

- **所属模块**: `include/core/` - 公共 API，`src/core/` - 实现
- **层级定位**: 绘图 API 的属性层，介于 `SkCanvas` 和底层渲染器之间
- **使用场景**: 所有 `SkCanvas` 绘图方法都接受 `SkPaint` 参数
- **作用范围**: 控制单次绘制操作的外观

## 主要类与结构体

### SkPaint 类

**继承关系**: 无继承（独立类）

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColor4f` | `SkColor4f` | RGBA 颜色（浮点型，未预乘） |
| `fWidth` | `SkScalar` | 描边宽度 |
| `fMiterLimit` | `SkScalar` | 斜接限制（尖角变斜角的阈值） |
| `fPathEffect` | `sk_sp<SkPathEffect>` | 路径效果（如虚线、路径变形） |
| `fShader` | `sk_sp<SkShader>` | 着色器（如渐变、图案填充） |
| `fMaskFilter` | `sk_sp<SkMaskFilter>` | 遮罩滤镜（如模糊） |
| `fColorFilter` | `sk_sp<SkColorFilter>` | 颜色滤镜（如色调调整） |
| `fImageFilter` | `sk_sp<SkImageFilter>` | 图像滤镜（如阴影、位移） |
| `fBlender` | `sk_sp<SkBlender>` | 自定义混合函数 |
| `fBitfields` | 位域结构体 | 压缩存储的开关和枚举值 |

**位域字段** (`fBitfields`):

| 位域字段 | 位数 | 说明 |
|---------|------|------|
| `fAntiAlias` | 1 bit | 抗锯齿开关 |
| `fDither` | 1 bit | 抖动开关 |
| `fCapType` | 2 bits | 线帽类型 (Cap) |
| `fJoinType` | 2 bits | 线连接类型 (Join) |
| `fStyle` | 2 bits | 绘制样式 (Style) |
| `fPadding` | 24 bits | 预留位 |

### Style 枚举

```cpp
enum Style : uint8_t {
    kFill_Style,          // 填充几何体
    kStroke_Style,        // 描边几何体
    kStrokeAndFill_Style, // 同时描边和填充
};
```

### Cap 枚举（线帽）

```cpp
enum Cap {
    kButt_Cap,    // 无延伸（平头）
    kRound_Cap,   // 圆形线帽
    kSquare_Cap,  // 方形线帽（延伸半个宽度）
};
```

### Join 枚举（线连接）

```cpp
enum Join : uint8_t {
    kMiter_Join,  // 尖角连接（延伸至斜接限制）
    kRound_Join,  // 圆角连接
    kBevel_Join,  // 斜角连接（切断尖角）
};
```

## 公共 API 函数

### 构造与析构

| 函数 | 说明 |
|------|------|
| `SkPaint()` | 默认构造函数，创建不透明黑色填充画笔 |
| `SkPaint(const SkColor4f&, SkColorSpace*)` | 指定颜色和色彩空间的构造函数 |
| `SkPaint(const SkPaint&)` | 拷贝构造函数（浅拷贝，智能指针增加引用计数） |
| `SkPaint(SkPaint&&)` | 移动构造函数 |
| `~SkPaint()` | 析构函数，递减智能指针引用计数 |

### 基础属性

| 函数 | 说明 |
|------|------|
| `void reset()` | 重置为默认值 |
| `bool isAntiAlias()` | 获取抗锯齿状态 |
| `void setAntiAlias(bool)` | 设置抗锯齿 |
| `bool isDither()` | 获取抖动状态 |
| `void setDither(bool)` | 设置抖动（减少色带） |
| `Style getStyle()` | 获取绘制样式 |
| `void setStyle(Style)` | 设置绘制样式 |
| `void setStroke(bool)` | 快捷设置为描边或填充 |

### 颜色管理

| 函数 | 说明 |
|------|------|
| `SkColor getColor()` | 获取颜色（32位 ARGB） |
| `SkColor4f getColor4f()` | 获取颜色（浮点 RGBA） |
| `void setColor(SkColor)` | 设置颜色（32位） |
| `void setColor(const SkColor4f&, SkColorSpace*)` | 设置颜色（浮点+色彩空间） |
| `float getAlphaf()` | 获取透明度（0.0-1.0） |
| `void setAlphaf(float)` | 设置透明度 |
| `uint8_t getAlpha()` | 获取透明度（0-255） |
| `void setAlpha(U8CPU)` | 设置透明度（0-255） |
| `void setARGB(U8CPU a, U8CPU r, U8CPU g, U8CPU b)` | 设置 ARGB 分量 |

### 描边属性

| 函数 | 说明 |
|------|------|
| `SkScalar getStrokeWidth()` | 获取描边宽度 |
| `void setStrokeWidth(SkScalar)` | 设置描边宽度（0 为细线） |
| `SkScalar getStrokeMiter()` | 获取斜接限制 |
| `void setStrokeMiter(SkScalar)` | 设置斜接限制 |
| `Cap getStrokeCap()` | 获取线帽类型 |
| `void setStrokeCap(Cap)` | 设置线帽类型 |
| `Join getStrokeJoin()` | 获取线连接类型 |
| `void setStrokeJoin(Join)` | 设置线连接类型 |

### 效果器（Effects）

| 函数 | 说明 |
|------|------|
| `SkShader* getShader()` | 获取着色器（不增加引用计数） |
| `sk_sp<SkShader> refShader()` | 获取着色器（增加引用计数） |
| `void setShader(sk_sp<SkShader>)` | 设置着色器 |
| `SkColorFilter* getColorFilter()` | 获取颜色滤镜 |
| `sk_sp<SkColorFilter> refColorFilter()` | 获取颜色滤镜（增加引用） |
| `void setColorFilter(sk_sp<SkColorFilter>)` | 设置颜色滤镜 |
| `SkPathEffect* getPathEffect()` | 获取路径效果 |
| `sk_sp<SkPathEffect> refPathEffect()` | 获取路径效果（增加引用） |
| `void setPathEffect(sk_sp<SkPathEffect>)` | 设置路径效果 |
| `SkMaskFilter* getMaskFilter()` | 获取遮罩滤镜 |
| `sk_sp<SkMaskFilter> refMaskFilter()` | 获取遮罩滤镜（增加引用） |
| `void setMaskFilter(sk_sp<SkMaskFilter>)` | 设置遮罩滤镜 |
| `SkImageFilter* getImageFilter()` | 获取图像滤镜 |
| `sk_sp<SkImageFilter> refImageFilter()` | 获取图像滤镜（增加引用） |
| `void setImageFilter(sk_sp<SkImageFilter>)` | 设置图像滤镜 |

### 混合模式

| 函数 | 说明 |
|------|------|
| `std::optional<SkBlendMode> asBlendMode()` | 尝试获取混合模式枚举 |
| `SkBlendMode getBlendMode_or(SkBlendMode)` | 获取混合模式，不支持返回默认值 |
| `bool isSrcOver()` | 判断是否为 SrcOver 模式 |
| `void setBlendMode(SkBlendMode)` | 设置混合模式 |
| `SkBlender* getBlender()` | 获取自定义混合器 |
| `sk_sp<SkBlender> refBlender()` | 获取混合器（增加引用） |
| `void setBlender(sk_sp<SkBlender>)` | 设置自定义混合器 |

### 优化与查询

| 函数 | 说明 |
|------|------|
| `bool nothingToDraw()` | 判断是否无需绘制（如完全透明） |
| `bool canComputeFastBounds()` | 判断是否能快速计算边界 |
| `const SkRect& computeFastBounds(const SkRect&, SkRect*)` | 计算绘制后的边界 |
| `const SkRect& computeFastStrokeBounds(const SkRect&, SkRect*)` | 计算描边后的边界 |

## 内部实现细节

### 1. 默认值初始化

```cpp
SkPaint::SkPaint()
    : fColor4f{0, 0, 0, 1}  // 不透明黑色
    , fWidth{0}             // 细线
    , fMiterLimit{SkPaintDefaults_MiterLimit}  // 通常为 4.0
    , fBitfields{
        (unsigned)false,                  // fAntiAlias
        (unsigned)false,                  // fDither
        (unsigned)SkPaint::kDefault_Cap,  // kButt_Cap
        (unsigned)SkPaint::kDefault_Join, // kMiter_Join
        (unsigned)SkPaint::kFill_Style,   // kFill_Style
        0                                 // fPadding
    }
```

### 2. 颜色空间转换

```cpp
void SkPaint::setColor(const SkColor4f& color, SkColorSpace* colorSpace) {
    SkColorSpaceXformSteps steps{colorSpace, kUnpremul_SkAlphaType,
                                 sk_srgb_singleton(), kUnpremul_SkAlphaType};
    fColor4f = color.pinAlpha();  // 确保 alpha 在 [0,1]
    steps.apply(fColor4f.vec());   // 转换到 sRGB
}
```

颜色始终在内部存储为 sRGB 色彩空间的 `SkColor4f`。

### 3. 参数验证

所有 setter 函数都包含范围检查：

```cpp
void SkPaint::setStrokeWidth(SkScalar width) {
    if (width >= 0) {
        fWidth = width;
    } else {
#ifdef SK_REPORT_API_RANGE_CHECK
        SkDebugf("SkPaint::setStrokeWidth() called with negative value\n");
#endif
    }
}
```

### 4. 效果器管理

使用智能指针 `sk_sp<T>` 自动管理引用计数：

```cpp
void SkPaint::setShader(sk_sp<SkShader> shader) {
    fShader = std::move(shader);
}
```

### 5. nothingToDraw 优化

```cpp
bool SkPaint::nothingToDraw() const {
    auto bm = this->asBlendMode();
    switch (bm.value()) {
        case SkBlendMode::kSrcOver:
        case SkBlendMode::kSrcATop:
        case SkBlendMode::kDstOut:
        case SkBlendMode::kDstOver:
        case SkBlendMode::kPlus:
            if (0 == this->getAlpha()) {
                return !affects_alpha(fColorFilter.get()) &&
                       !affects_alpha(fImageFilter.get());
            }
            break;
        case SkBlendMode::kDst:
            return true;
        default:
            break;
    }
    return false;
}
```

提前剪枝无效绘制操作以提高性能。

### 6. 边界计算

```cpp
const SkRect& SkPaint::doComputeFastBounds(const SkRect& origSrc,
                                           SkRect* storage,
                                           Style style) const {
    const SkRect* src = &origSrc;
    SkRect tmpSrc;

    // 1. 应用路径效果
    if (this->getPathEffect()) {
        tmpSrc = origSrc;
        as_PEB(this->getPathEffect())->computeFastBounds(&tmpSrc);
        src = &tmpSrc;
    }

    // 2. 应用描边膨胀
    SkScalar radius = SkStrokeRec::GetInflationRadius(*this, style);
    *storage = src->makeOutset(radius, radius);

    // 3. 应用遮罩滤镜
    if (this->getMaskFilter()) {
        as_MFB(this->getMaskFilter())->computeFastBounds(*storage, storage);
    }

    // 4. 应用图像滤镜
    if (this->getImageFilter()) {
        *storage = this->getImageFilter()->computeFastBounds(*storage);
    }

    return *storage;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkColor.h` | 颜色定义 |
| `SkShader.h` | 着色器接口 |
| `SkColorFilter.h` | 颜色滤镜接口 |
| `SkPathEffect.h` | 路径效果接口 |
| `SkMaskFilter.h` | 遮罩滤镜接口 |
| `SkImageFilter.h` | 图像滤镜接口 |
| `SkBlender.h` | 混合器接口 |
| `SkColorSpace.h` | 色彩空间管理 |
| `SkStrokeRec.h` | 描边参数记录 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `SkCanvas` | 所有绘图方法接受 `SkPaint` 参数 |
| `SkDevice` | 设备层需要解析 `SkPaint` 属性 |
| `SkDraw` | 底层绘制实现使用 `SkPaint` |
| `SkRasterPipeline` | 将 `SkPaint` 转换为管线阶段 |
| `SkGpuDevice` | GPU 渲染需要转换 `SkPaint` 到着色器 |

## 设计模式与设计决策

### 1. 值语义与智能指针结合

- **基础属性**（颜色、宽度）采用值语义
- **效果器**（shader、filter）采用智能指针共享

**理由**: 效果器通常是不可变对象且创建成本高，共享可减少内存占用。

### 2. 位域压缩

将多个布尔和小范围枚举压缩到 32 位整数：

```cpp
union {
    struct {
        unsigned fAntiAlias : 1;
        unsigned fDither : 1;
        unsigned fCapType : 2;
        unsigned fJoinType : 2;
        unsigned fStyle : 2;
        unsigned fPadding : 24;
    } fBitfields;
    uint32_t fBitfieldsUInt;  // 用于快速比较
};
```

**优势**:
- 减小对象大小（`sizeof(SkPaint)` 约 80 字节）
- 提高缓存命中率
- 支持快速相等性比较

### 3. 不可变效果器

所有效果器（`SkShader`, `SkColorFilter` 等）创建后不可修改：

```cpp
// SkShader 等没有 setter 方法
```

**理由**: 支持跨线程共享且无需锁，简化并发渲染。

### 4. 混合模式的双重接口

- `setBlendMode(SkBlendMode)`: 简单场景
- `setBlender(sk_sp<SkBlender>)`: 自定义混合逻辑

**设计意图**: 兼顾易用性和扩展性。

### 5. 浅拷贝语义

```cpp
SkPaint copy = original;  // 智能指针增加引用计数
```

**影响**:
- 拷贝成本低（仅复制指针）
- 修改效果器需要创建新对象

### 6. 类型安全的标志位

使用强类型枚举而非整数标志：

```cpp
enum class Style : uint8_t { ... };
```

防止错误类型混用。

## 性能考量

### 1. 对象大小优化

通过位域和智能指针，`SkPaint` 大小约 80 字节，适合栈上分配。

### 2. 快速路径检测

```cpp
if (kFill_Style == style) {
    uintptr_t effects = 0;
    effects |= reinterpret_cast<uintptr_t>(this->getMaskFilter());
    effects |= reinterpret_cast<uintptr_t>(this->getPathEffect());
    effects |= reinterpret_cast<uintptr_t>(this->getImageFilter());
    if (!effects) {
        return orig;  // 无需计算边界
    }
}
```

使用指针位运算快速检测是否有效果器。

### 3. 避免虚函数

`SkPaint` 本身不包含虚函数，避免虚表开销。

### 4. 引用计数优化

智能指针的原子操作在单线程场景可能成为瓶颈，但效果器不可变性允许共享。

### 5. 边界计算缓存

`computeFastBounds` 接受输出参数避免分配：

```cpp
SkRect storage;
const SkRect& result = paint.computeFastBounds(orig, &storage);
```

### 6. 内存布局

成员变量按访问频率和大小排列，智能指针在前（最常访问）。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkCanvas.h` | 使用 `SkPaint` 的主要绘图接口 |
| `include/core/SkShader.h` | 着色器基类 |
| `include/core/SkColorFilter.h` | 颜色滤镜基类 |
| `include/core/SkPathEffect.h` | 路径效果基类 |
| `include/core/SkMaskFilter.h` | 遮罩滤镜基类 |
| `include/core/SkImageFilter.h` | 图像滤镜基类 |
| `include/core/SkBlender.h` | 混合器基类 |
| `src/core/SkPaintDefaults.h` | 默认值定义 |
| `src/core/SkPaintPriv.h` | 内部辅助函数 |
| `src/core/SkDraw.cpp` | 使用 `SkPaint` 的底层绘制实现 |
| `src/core/SkRasterPipeline.cpp` | 将 `SkPaint` 转换为渲染管线 |
