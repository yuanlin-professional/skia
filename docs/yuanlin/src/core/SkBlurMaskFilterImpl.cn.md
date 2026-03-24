# SkBlurMaskFilterImpl

> 源文件：src/core/SkBlurMaskFilterImpl.h, src/core/SkBlurMaskFilterImpl.cpp

## 概述

`SkBlurMaskFilterImpl` 是 Skia 中模糊遮罩滤镜（Blur Mask Filter）的核心实现类，继承自 `SkMaskFilterBase`。它封装了高斯模糊效果，支持将模糊应用于绘制路径、文本和图形的遮罩层，实现阴影、发光等视觉效果。

核心功能：
- 四种模糊样式（Normal、Solid、Inner、Outer）
- 可选的 CTM（坐标变换矩阵）响应模式
- 矩形和圆角矩形的快速路径优化
- 九宫格（Nine-Patch）缓存机制
- 与图像滤镜的互操作性

## 架构位置

```
SkPaint
  └── SkMaskFilter (公共接口)
        └── SkMaskFilterBase (内部基类)
              └── SkBlurMaskFilterImpl (模糊实现)
                    ├── SkBlurMask (底层模糊算法)
                    ├── SkMaskCache (九宫格缓存)
                    └── SkImageFilters (转换为图像滤镜)
```

作为 `SkMaskFilter` 的具体实现，`SkBlurMaskFilterImpl` 桥接上层绘制 API 和底层模糊算法。

## 主要类与结构体

### SkBlurMaskFilterImpl

**继承关系：**`SkMaskFilterBase` -> `SkFlattenable`

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fSigma | SkScalar | 高斯模糊标准差 |
| fBlurStyle | SkBlurStyle | 模糊样式枚举 |
| fRespectCTM | bool | 是否响应坐标变换 |

**核心方法：**

| 方法 | 说明 |
|------|------|
| `filterMask()` | 对遮罩应用模糊 |
| `filterRectMask()` | 矩形快速模糊 |
| `filterRRectToNine()` | 圆角矩形九宫格优化 |
| `filterRectsToNine()` | 矩形九宫格优化 |
| `asImageFilter()` | 转换为图像滤镜 |
| `computeXformedSigma()` | 计算变换后的 sigma |

## 公共 API 函数

### 1. 构造函数

```cpp
SkBlurMaskFilterImpl(SkScalar sigma, SkBlurStyle style, bool respectCTM)
```

**参数：**
- `sigma`: 模糊强度（标准差），必须 > 0
- `style`: 模糊样式（见下表）
- `respectCTM`: `true` 时模糊强度随坐标变换缩放，`false` 时保持设备空间恒定

**模糊样式：**

| 样式 | 效果 | 公式 |
|------|------|------|
| kNormal | 标准模糊 | dst = blur(src) |
| kSolid | 实心效果 | dst = src + blur(src) - src × blur(src) |
| kOuter | 外发光 | dst = blur(src) × (1 - src) |
| kInner | 内发光 | dst = blur(src) × src |

### 2. 遮罩滤镜接口

```cpp
bool filterMask(SkMaskBuilder* dst, const SkMask& src,
                const SkMatrix& matrix, SkIPoint* margin) const override
```

**功能：**对输入遮罩应用模糊，生成输出遮罩。

**返回值：**成功返回 `true`，失败（如内存不足）返回 `false`。

### 3. 转换为图像滤镜

```cpp
std::pair<sk_sp<SkImageFilter>, bool> asImageFilter(const SkMatrix& ctm,
                                                     const SkPaint&) const override
```

**功能：**将遮罩滤镜转换为等效的图像滤镜（`SkBlurImageFilter`），以便在层混合和硬件加速场景中使用。

**返回值：**
- `first`: 图像滤镜对象
- `second`: `false` 表示滤镜不需要后处理

**实现细节：**
- **Normal**: 直接模糊
- **Solid**: 使用 `SkBlendMode::kSrcOver` 混合
- **Outer**: 使用 `SkBlendMode::kDstOut` 混合
- **Inner**: 使用 `SkBlendMode::kDstIn` 混合

### 4. 变换 Sigma 计算

```cpp
SkScalar computeXformedSigma(const SkMatrix& ctm) const
```

**功能：**根据坐标变换矩阵计算实际的模糊强度。

**逻辑：**
- 如果 `!fRespectCTM`，直接返回 `fSigma`
- 否则，计算 `ctm.mapRadius(fSigma)`，并限制在 128 以内

### 5. 快速边界计算

```cpp
void computeFastBounds(const SkRect& src, SkRect* dst) const override
```

**功能：**快速估算模糊后的边界扩展。

**公式：**`pad = 3.0 * fSigma`（基于 3σ 原则）

## 内部实现细节

### 1. 九宫格优化

九宫格技术将大型圆角矩形模糊拆解为：
- 4 个角（固定大小）
- 4 条边（可拉伸）
- 1 个中心（可拉伸）

**算法流程：**

```cpp
// 1. 计算最小九宫格尺寸
int leftUnstretched = ceil(max(radii_UL.x, radii_LL.x)) + margin.x;
int rightUnstretched = ceil(max(radii_UR.x, radii_LR.x)) + margin.x;
int totalSmallWidth = leftUnstretched + rightUnstretched + 1;

// 2. 构建小型圆角矩形
SkRRect smallRR = ...;

// 3. 查找缓存或执行模糊
cached = find_cached_rrect(smallRR);
if (!cached) {
    draw_rrect_into_mask(smallRR, &srcM);
    filterMask(&filterM, srcM, ...);
    cached = add_cached_rrect(&filterM, smallRR);
}

// 4. 返回九宫格数据
return NinePatch{mask, bounds, center, cached};
```

**优势：**
- 缓存重用：相同圆角半径的矩形共享模糊结果
- 性能提升：仅模糊小型九宫格，避免处理整个大矩形

### 2. 矩形快速路径

对于标准矩形，使用 `SkBlurMask::BlurRect()` 的解析式模糊：

```cpp
bool filterRectMask(SkMaskBuilder* dst, const SkRect& r,
                    const SkMatrix& matrix, SkIPoint* margin,
                    SkMaskBuilder::CreateMode createMode) const {
    SkScalar sigma = computeXformedSigma(matrix);
    return SkBlurMask::BlurRect(sigma, dst, r, fBlurStyle, margin, createMode);
}
```

比通用路径快 10~100 倍。

### 3. 嵌套矩形处理

对于环形区域（外矩形 - 内矩形），使用 EvenOdd 填充规则绘制：

```cpp
SkPath path = SkPathBuilder()
    .addRect(outerRect)
    .addRect(innerRect)
    .setFillType(SkPathFillType::kEvenOdd)
    .detach();
draw.drawPath(path, paint, nullptr);
```

### 4. CTM 非响应模式的 Sigma 计算

当 `!fRespectCTM` 时，需要在图像滤镜转换中反向补偿变换：

```cpp
const float xScaleFactor = fSigma / ctm.mapVector(fSigma, 0.f).length();
const float yScaleFactor = fSigma / ctm.mapVector(0.f, fSigma).length();
sigma = {fSigma * xScaleFactor, fSigma * yScaleFactor};
```

这确保在变换后的空间中，模糊效果在设备像素级别保持恒定。

### 5. 缓存键生成

缓存系统使用 `(sigma, style, geometry)` 三元组作为键：

```cpp
// 圆角矩形
SkCachedData* find_cached_rrect(SkScalar sigma, SkBlurStyle style,
                                const SkRRect& rrect, ...);

// 矩形数组
SkCachedData* find_cached_rects(SkScalar sigma, SkBlurStyle style,
                                SkSpan<const SkRect> rects, ...);
```

### 6. 遮罩绘制管线

`draw_into_mask()` 使用 CPU 光栅化管线：

```cpp
skcpu::Draw draw;
draw.fBlitterChooser = SkA8Blitter_Choose;  // 使用 A8 混合器
draw.fCTM = &ctm;
draw.fDst = pixmap;
draw.fRC = &rasterClip;

SkPaint paint;
paint.setAntiAlias(true);
proc(draw, paint);  // 调用者提供的绘制回调
```

这确保遮罩生成完全在 CPU 执行，无需 GPU 上下文。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkMaskFilterBase` | 基类接口 |
| `SkBlurMask` | 底层模糊算法 |
| `SkMaskCache` | 九宫格缓存管理 |
| `SkCachedData` | 缓存数据封装 |
| `SkImageFilters` | 图像滤镜转换 |
| `SkDraw` | CPU 绘制管线 |
| `SkA8Blitter` | A8 格式混合器 |
| `SkResourceCache` | 全局资源缓存 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `SkMaskFilter` | 通过工厂方法创建 |
| `SkPaint` | 通过 `setMaskFilter()` 应用 |
| `SkCanvas` | 绘制文本和路径时自动应用 |
| `SkDraw` | 光栅化过程中调用 `filterMask()` |

## 设计模式与设计决策

### 1. 策略模式

不同模糊样式使用统一接口，通过 `fBlurStyle` 枚举切换：

```cpp
switch(fBlurStyle) {
    case kNormal: /* 标准模糊 */ break;
    case kSolid:  /* 叠加处理 */ break;
    case kOuter:  /* 减法处理 */ break;
    case kInner:  /* 乘法处理 */ break;
}
```

### 2. 工厂方法模式

通过 `SkMaskFilter::MakeBlur()` 创建实例：

```cpp
sk_sp<SkMaskFilter> SkMaskFilter::MakeBlur(SkBlurStyle style, SkScalar sigma,
                                           bool respectCTM) {
    if (SkIsFinite(sigma) && sigma > 0) {
        return sk_sp<SkMaskFilter>(new SkBlurMaskFilterImpl(sigma, style, respectCTM));
    }
    return nullptr;
}
```

### 3. 适配器模式

`asImageFilter()` 将遮罩滤镜适配为图像滤镜接口，实现跨 API 兼容。

### 4. 享元模式

九宫格缓存共享相同几何参数的模糊结果，节省内存和计算：

```cpp
if (cached = find_cached_rrect(sigma, style, smallRR)) {
    return cached;  // 重用
}
// 否则计算并缓存
```

### 5. 模板方法模式

`draw_into_mask()` 定义了遮罩生成的通用流程，具体绘制由回调函数提供：

```cpp
template <typename Proc>
bool draw_into_mask(SkMaskBuilder* mask, const SkRect& bounds, Proc proc) {
    prepare_to_draw_into_mask(bounds, mask);
    // ... 设置绘制上下文 ...
    proc(draw, paint);  // 调用者提供的绘制逻辑
    return true;
}
```

### 6. 延迟评估

`filterRectsToNine()` 先计算边界，再决定是否分配内存：

```cpp
// 第一次调用：仅计算边界
this->filterRectMask(&dstM, rects[0], matrix, &margin,
                     SkMaskBuilder::kJustComputeBounds_CreateMode);
// 检查是否可行
if (dx < 0 || dy < 0) return FilterReturn::kUnimplemented;
// 第二次调用：实际渲染
this->filterRectMask(&filterM, smallR[0], matrix, nullptr,
                     SkMaskBuilder::kComputeBoundsAndRenderImage_CreateMode);
```

## 性能考量

### 1. 快速路径判断

```cpp
// 矩形直接使用解析式模糊
if (rrect.getType() == SkRRect::kRect_Type) {
    return filterRectMask(...);
}

// 圆角矩形尝试九宫格
if (canUseNinePatch(rrect, style)) {
    return filterRRectToNine(...);
}

// 兜底：通用路径
return filterMask(...);
```

### 2. 九宫格缓存效率

**缓存命中率：**UI 中常见相同圆角半径的按钮、卡片等，命中率 > 80%。

**内存占用：**小型九宫格（通常 < 100×100）远小于完整矩形（可能 1000×1000+）。

### 3. Sigma 上限

```cpp
constexpr SkScalar kMaxBlurSigma = SkIntToScalar(128);
SkScalar xformedSigma = std::min(ctm.mapRadius(fSigma), kMaxBlurSigma);
```

防止极大 sigma 值导致计算爆炸，超过此值应由调用者降采样。

### 4. 内存分配优化

**预分配：**使用 `SkMaskBuilder` 的 `kZeroInit_Alloc` 避免手动清零。

**原地处理：**某些模糊样式直接修改输入遮罩，无需额外分配。

### 5. 性能数据（估算）

| 场景 | 方法 | 相对性能 |
|------|------|---------|
| 小矩形阴影 | 解析式模糊 | 1.0× |
| 大矩形阴影 | 九宫格（首次） | 10× |
| 大矩形阴影 | 九宫格（缓存） | 50× |
| 圆角矩形 | 九宫格 | 20× |
| 复杂路径 | 通用模糊 | 0.1× |

### 6. 性能陷阱

**过大 Sigma：**未限制的 sigma 会导致巨大卷积核，建议在外部检测并降采样。

**缓存未命中：**频繁改变圆角半径会导致缓存失效，应尽量复用相同参数。

**Inner 样式内存：**kInner 需要额外分配与源遮罩相同大小的缓冲区。

## 相关文件

| 文件 | 关系 | 说明 |
|-----|------|------|
| src/core/SkMaskFilterBase.h | 基类 | 遮罩滤镜抽象接口 |
| src/core/SkBlurMask.h | 算法实现 | 底层模糊算法 |
| src/core/SkMaskCache.h | 缓存管理 | 九宫格缓存系统 |
| src/core/SkCachedData.h | 数据封装 | 缓存数据生命周期管理 |
| include/effects/SkImageFilters.h | 图像滤镜 | 模糊图像滤镜 API |
| include/core/SkMaskFilter.h | 公共接口 | 遮罩滤镜工厂 |
| include/core/SkBlurTypes.h | 枚举类型 | 模糊样式定义 |
