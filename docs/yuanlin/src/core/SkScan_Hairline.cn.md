# SkScan_Hairline

> 源文件
> - src/core/SkScan_Hairline.cpp

## 概述

`SkScan_Hairline.cpp` 实现了 Skia 中非反走样细线(hairline)和路径描边的光栅化算法。该模块负责将1像素宽的直线、曲线(二次、三次贝塞尔曲线、圆锥曲线)转换为像素,支持不同的端点样式(Butt/Square/Round Cap),并通过递归细分和优化的快速路径实现高效渲染。它是 Skia 矢量图形渲染管道中的关键组件,广泛用于路径描边和线段绘制。

## 架构位置

`SkScan_Hairline` 位于 Skia 扫描转换子系统中:

- **SkScan 家族**: 与 `SkScan_Antihair.cpp`(反走样版本)并列
- **几何转换**: 将曲线细分为直线段
- **像素化**: 调用 `SkBlitter` 填充像素
- **快速路径**: 针对简单形状的优化版本

## 主要类与结构体

### 核心数据结构

本文件主要使用模板函数和内联类,无大型类定义。主要依赖:

| 类型 | 来源 | 用途 |
|------|------|------|
| `SkPathRaw` | `src/core/SkPathRaw.h` | 底层路径表示 |
| `SkBlitter` | `src/core/SkBlitter.h` | 像素填充接口 |
| `SkRasterClip` | `src/core/SkRasterClip.h` | 裁剪区域 |
| `SkQuadCoeff` | `src/core/SkGeometry.h` | 二次曲线系数 |
| `SkCubicCoeff` | `src/core/SkGeometry.h` | 三次曲线系数 |

### 直线绘制辅助函数

```cpp
// 水平主导的直线
static void horiline(int x, int stopx, SkFixed fy, SkFixed dy,
                     SkBlitter* blitter);

// 垂直主导的直线
static void vertline(int y, int stopy, SkFixed fx, SkFixed dx,
                     SkBlitter* blitter);
```

## 公共 API 函数

### 直线绘制

```cpp
// 绘制直线序列(区域裁剪版本)
void SkScan::HairLineRgn(SkSpan<const SkPoint> src,
                         const SkRegion* clip,
                         SkBlitter* blitter);

// 绘制直线序列(光栅裁剪版本)
void SkScan::HairLine(SkSpan<const SkPoint> pts,
                      const SkRasterClip& clip,
                      SkBlitter* blitter);
```

### 路径描边

```cpp
// 无端点样式
void SkScan::HairPath(const SkPathRaw& raw,
                      const SkRasterClip& clip,
                      SkBlitter* blitter);

// 方形端点
void SkScan::HairSquarePath(const SkPathRaw& raw,
                             const SkRasterClip& clip,
                             SkBlitter* blitter);

// 圆形端点
void SkScan::HairRoundPath(const SkPathRaw& raw,
                           const SkRasterClip& clip,
                           SkBlitter* blitter);
```

### 矩形框绘制

```cpp
// 绘制矩形边框(仅边框)
void SkScan::HairRect(const SkRect& rect,
                      const SkRasterClip& clip,
                      SkBlitter* blitter);

// 绘制带线宽的矩形框
void SkScan::FrameRect(const SkRect& r,
                       const SkPoint& strokeSize,
                       const SkRasterClip& clip,
                       SkBlitter* blitter);
```

## 内部实现细节

### 直线光栅化策略

根据斜率选择不同的遍历方向:

```cpp
void SkScan::HairLineRgn(SkSpan<const SkPoint> src, ...) {
    for (size_t i = 0; i < src.size() - 1; ++i) {
        // 转换为 FDot6 坐标
        SkFDot6 x0 = SkScalarToFDot6(pts[0].fX);
        SkFDot6 y0 = SkScalarToFDot6(pts[0].fY);
        SkFDot6 x1 = SkScalarToFDot6(pts[1].fX);
        SkFDot6 y1 = SkScalarToFDot6(pts[1].fY);

        SkFDot6 dx = x1 - x0;
        SkFDot6 dy = y1 - y0;

        if (SkAbs32(dx) > SkAbs32(dy)) {  // 近水平
            if (x0 > x1) { swap(x0, x1); swap(y0, y1); }
            SkFixed slope = SkFixedDiv(dy, dx);
            SkFixed startY = SkFDot6ToFixed(y0) + ...;
            horiline(ix0, ix1, startY, slope, blitter);
        } else {  // 近垂直
            if (y0 > y1) { swap(x0, x1); swap(y0, y1); }
            SkFixed slope = SkFixedDiv(dx, dy);
            SkFixed startX = SkFDot6ToFixed(x0) + ...;
            vertline(iy0, iy1, startX, slope, blitter);
        }
    }
}
```

### 水平/垂直线优化

```cpp
static void horiline(int x, int stopx, SkFixed fy, SkFixed dy,
                     SkBlitter* blitter) {
    // 检查是否可以直接像素访问
    if (auto direct = blitter->canDirectBlit()) {
        const auto pm = direct->pm;
        const auto value = direct->value;

        // 根据像素格式调度(1/2/4/8字节)
        switch (pm.info().bytesPerPixel()) {
            case 4:
                do {
                    *pm.writable_addr32(x, fy >> 16) = value;
                    fy += dy;
                } while (++x < stopx);
                break;
            // ... 其他格式
        }
    } else {
        // 回退到通用 blitter
        do {
            blitter->blitH(x, fy >> 16, 1);
            fy += dy;
        } while (++x < stopx);
    }
}
```

**直接像素访问优化**:
- 避免虚函数调用开销
- 编译器可内联和向量化
- 对于简单颜色填充,可能快5-10倍

### 二次贝塞尔曲线细分

```cpp
static void hair_quad(const SkPoint pts[3], const SkRegion* clip,
                      SkBlitter* blitter, int level,
                      SkScan::HairRgnProc lineproc) {
    // 转换为二次曲线系数: p(t) = At^2 + Bt + C
    SkQuadCoeff coeff(pts);

    const unsigned lines = 1 << level;  // 细分级别 -> 线段数
    float2 t(0);
    float2 dt(1.0f / lines);

    SkPoint tmp[(1 << kMaxQuadSubdivideLevel) + 1];
    tmp[0] = pts[0];

    float2 A = coeff.fA;
    float2 B = coeff.fB;
    float2 C = coeff.fC;
    mask2 is_finite(~0);  // 检测 NaN/Inf

    // 使用 SIMD 计算所有点
    for (unsigned i = 1; i < lines; ++i) {
        t = t + dt;
        float2 p = (A * t + B) * t + C;  // 霍纳法则
        is_finite &= float2_is_finite(p);
        p.store(&tmp[i]);
    }

    if (all(is_finite)) {
        tmp[lines] = pts[2];
        lineproc({tmp, lines + 1}, clip, blitter);  // 绘制线段序列
    }
}
```

**细分级别计算**:

```cpp
static int compute_quad_level(const SkPoint pts[3]) {
    // 计算控制点到端点连线的距离
    uint32_t d = compute_int_quad_dist(pts);

    // 每次细分距离减少4倍,计算达到1像素所需细分次数
    int level = (33 - SkCLZ(d)) >> 1;  // log4(d)
    return std::min(level, kMaxQuadSubdivideLevel);
}

static uint32_t compute_int_quad_dist(const SkPoint pts[3]) {
    // 向量: 控制点到端点中点
    SkScalar dx = SkScalarHalf(pts[0].fX + pts[2].fX) - pts[1].fX;
    SkScalar dy = SkScalarHalf(pts[0].fY + pts[2].fY) - pts[1].fY;

    // 曼哈顿距离近似
    uint32_t idx = SkScalarCeilToInt(SkScalarAbs(dx));
    uint32_t idy = SkScalarCeilToInt(SkScalarAbs(dy));

    return (idx > idy) ? idx + (idy >> 1) : idy + (idx >> 1);
}
```

### 三次贝塞尔曲线细分

```cpp
static void hair_cubic(const SkPoint pts[4], const SkRegion* clip,
                       SkBlitter* blitter, SkScan::HairRgnProc lineproc) {
    const size_t lines = compute_cubic_segs(pts);

    if (lines == 1) {
        // 退化为直线
        lineproc({{pts[0], pts[3]}}, clip, blitter);
        return;
    }

    // p(t) = At^3 + Bt^2 + Ct + D
    SkCubicCoeff coeff(pts);

    float2 t(0);
    const float2 dt(1.0f / lines);

    SkPoint tmp[(1 << kMaxCubicSubdivideLevel) + 1];
    tmp[0] = pts[0];

    float2 A = coeff.fA;
    float2 B = coeff.fB;
    float2 C = coeff.fC;
    float2 D = coeff.fD;

    for (unsigned i = 1; i < lines; ++i) {
        t = t + dt;
        float2 p = ((A * t + B) * t + C) * t + D;  // 霍纳法则
        p.store(&tmp[i]);
    }

    tmp[lines] = pts[3];
    lineproc({tmp, lines + 1}, clip, blitter);
}
```

**细分级别计算(三次曲线)**:

```cpp
static inline int compute_cubic_segs(const SkPoint pts[4]) {
    // 近似为两条二次曲线的最大偏差
    float2 p0 = from_point(pts[0]);
    float2 p1 = from_point(pts[1]);
    float2 p2 = from_point(pts[2]);
    float2 p3 = from_point(pts[3]);

    float2 p13 = oneThird * p3 + twoThird * p0;
    float2 p23 = oneThird * p0 + twoThird * p3;

    SkScalar diff = max_component(max(abs(p1 - p13), abs(p2 - p23)));

    // 每次细分误差减少4倍
    SkScalar tol = SK_Scalar1 / 8;
    for (int i = 0; i < kMaxCubicSubdivideLevel; ++i) {
        if (diff < tol) return 1 << i;
        tol *= 4;
    }
    return 1 << kMaxCubicSubdivideLevel;
}
```

### 端点扩展(Cap Style)

```cpp
template <SkPaint::Cap capStyle>
void extend_pts(std::optional<SkPathVerb> prevVerb,
                std::optional<SkPathVerb> nextVerb,
                SkSpan<SkPoint> pts) {
    // Round/Square cap 扩展 1/2 单位长度
    const SkScalar capOutset = (capStyle == SkPaint::kSquare_Cap)
                                ? 0.5f
                                : SK_ScalarPI / 8;  // 圆形面积的一半

    // 起点扩展(如果前一个动词是 Move)
    if (optional_eq(prevVerb, SkPathVerb::kMove)) {
        SkPoint* first = pts.data();
        SkVector tangent = *first - *(first + 1);  // 起始切线

        if (tangent.isZero()) {
            tangent.set(1, 0);  // 退化情况
        } else {
            tangent.normalize();
        }

        first->fX += tangent.fX * capOutset;
        first->fY += tangent.fY * capOutset;
    }

    // 终点扩展(如果下一个动词是 Move/Close/结束)
    if (!nextVerb.has_value() ||
        nextVerb.value() == SkPathVerb::kMove ||
        nextVerb.value() == SkPathVerb::kClose) {
        SkPoint* last = &pts.back();
        SkVector tangent = *last - *(last - 1);  // 结束切线

        if (!tangent.isZero()) {
            tangent.normalize();
        }

        last->fX += tangent.fX * capOutset;
        last->fY += tangent.fY * capOutset;
    }
}
```

### 路径遍历与裁剪优化

```cpp
template <SkPaint::Cap capStyle>
void hair_path(const SkPathRaw& raw, const SkRasterClip& rclip,
               SkBlitter* blitter, SkScan::HairRgnProc lineproc) {
    // 预计算裁剪边界
    SkRect insetStorage, outsetStorage;
    const SkRect* insetClip = nullptr;
    const SkRect* outsetClip = nullptr;

    if (!rclip.quickContains(ibounds)) {
        insetStorage.set(clip->getBounds());
        outsetStorage = insetStorage.makeOutset(1, 1);
        insetStorage.inset(1, 1);

        if (is_inverted(insetStorage)) {
            insetStorage.setEmpty();  // 太小无法快速接受
        }

        insetClip = &insetStorage;   // 快速接受边界
        outsetClip = &outsetStorage;  // 快速拒绝边界
    }

    // 遍历路径段
    for (auto rec : raw.iter()) {
        switch (rec->fVerb) {
            case SkPathVerb::kQuad: {
                std::copy(srcPts, srcPts + 3, pts);
                if (capStyle != SkPaint::kButt_Cap) {
                    extend_pts<capStyle>(prevVerb, nextVerb, {pts, 3});
                }

                // 裁剪优化检查
                if (insetClip) {
                    SkRect bounds = compute_nocheck_quad_bounds(pts);
                    if (!geometric_overlap(*outsetClip, bounds)) {
                        continue;  // 完全在外,跳过
                    }
                    if (geometric_contains(*insetClip, bounds)) {
                        clip = nullptr;  // 完全在内,禁用裁剪
                    }
                }

                hairquad(pts, clip, insetClip, outsetClip, blitter, level, lineproc);
                break;
            }
            // ... Cubic, Conic 等类似处理
        }
    }
}
```

### 矩形框优化

```cpp
void SkScan::HairRect(const SkRect& rect, const SkRasterClip& clip,
                      SkBlitter* blitter) {
    SkIRect r = SkIRect::MakeLTRB(
        SkScalarFloorToInt(rect.fLeft),
        SkScalarFloorToInt(rect.fTop),
        SkScalarFloorToInt(rect.fRight + 1),   // 包含右边
        SkScalarFloorToInt(rect.fBottom + 1)   // 包含底边
    );

    if (width <= 2 || height <= 2) {
        // 小矩形优化: 直接填充
        blitter->blitRect(r.fLeft, r.fTop, width, height);
        return;
    }

    // 分四条边绘制
    blitter->blitH(r.fLeft, r.fTop, width);                     // 上
    blitter->blitRect(r.fLeft, r.fTop + 1, 1, height - 2);      // 左
    blitter->blitRect(r.fRight - 1, r.fTop + 1, 1, height - 2); // 右
    blitter->blitH(r.fLeft, r.fBottom - 1, width);              // 下
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBlitter` | 像素填充 |
| `SkFDot6` | 定点数运算 |
| `SkGeometry` | 曲线系数计算 |
| `SkLineClipper` | 直线裁剪 |
| `SkAutoConicToQuads` | 圆锥曲线转二次曲线 |
| `skvx` (SkVx.h) | SIMD 向量运算 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkDraw` | 路径描边调度 |
| `SkCanvas` | 用户 API |
| `SkPaint::Stroke` | 描边参数 |

## 设计模式与设计决策

### 1. 模板方法模式

端点样式通过模板参数特化:

```cpp
template <SkPaint::Cap capStyle>
void hair_path(...) {
    if (capStyle != SkPaint::kButt_Cap) {
        extend_pts<capStyle>(...);
    }
    // ...
}

// 实例化三个版本
void HairPath(...) { hair_path<SkPaint::kButt_Cap>(...); }
void HairSquarePath(...) { hair_path<SkPaint::kSquare_Cap>(...); }
void HairRoundPath(...) { hair_path<SkPaint::kRound_Cap>(...); }
```

### 2. 策略模式

不同曲线类型使用不同细分策略:
- **二次曲线**: `hair_quad` + 距离启发式
- **三次曲线**: `hair_cubic` + 偏差启发式
- **圆锥曲线**: 先转换为二次曲线序列

### 3. 快速路径优化

```cpp
// 裁剪快速路径
if (geometric_contains(*insetClip, bounds)) {
    clip = nullptr;  // 完全在内,跳过裁剪检查
}

// 直线快速路径
if (auto direct = blitter->canDirectBlit()) {
    // 直接像素访问
}

// 矩形快速路径
if (width <= 2 || height <= 2) {
    blitter->blitRect(...);  // 直接填充
}
```

### 4. 设计权衡

**为什么递归细分而不是解析求交?**

| 方法 | 优点 | 缺点 |
|------|------|------|
| 递归细分 | 简单、稳定、可预测 | 可能过度细分 |
| 解析求交 | 精确、最少线段 | 数值不稳定、复杂 |

**为什么使用 FDot6?**
- **精度**: 1/64 像素足够细线
- **性能**: 整数运算比浮点快
- **兼容性**: 与其他模块一致

## 性能考量

### 1. SIMD 曲线求值

```cpp
// 使用 skvx 向量类型
float2 t(0);
float2 dt(1.0f / lines);

for (unsigned i = 1; i < lines; ++i) {
    t = t + dt;
    float2 p = (A * t + B) * t + C;  // 2个浮点运算同时执行
    p.store(&tmp[i]);
}
```

### 2. 直接像素访问

避免虚函数调用:

```cpp
// 慢速路径(每像素虚函数调用)
for (int x = x0; x < x1; x++) {
    blitter->blitH(x, y, 1);  // 虚函数
}

// 快速路径(直接内存写入)
for (int x = x0; x < x1; x++) {
    *pm.writable_addr32(x, y) = value;  // 直接访问
}
```

**性能提升**: 5-10x

### 3. 裁剪边界缓存

```cpp
// 预计算裁剪边界,避免重复计算
const SkRect* insetClip = &insetStorage;   // 一次计算
const SkRect* outsetClip = &outsetStorage;

// 快速拒绝/接受检查
if (!geometric_overlap(*outsetClip, bounds)) continue;
if (geometric_contains(*insetClip, bounds)) clip = nullptr;
```

### 4. 细分级别限制

```cpp
#define kMaxQuadSubdivideLevel  5   // 最多 32 段
#define kMaxCubicSubdivideLevel 9   // 最多 512 段

// 避免病态曲线导致指数爆炸
int level = std::min(computed_level, kMaxQuadSubdivideLevel);
```

### 5. 栈分配临时数组

```cpp
SkPoint tmp[(1 << kMaxCubicSubdivideLevel) + 1];  // 栈分配 513 个点
// 避免堆分配开销
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkScan_Hairline.cpp` | 本文件(非反走样细线) |
| `src/core/SkScan_Antihair.cpp` | 反走样细线实现 |
| `src/core/SkBlitter.h` | 像素填充接口 |
| `src/core/SkGeometry.h` | 曲线系数和工具 |
| `src/core/SkLineClipper.h` | 直线裁剪 |
| `src/base/SkVx.h` | SIMD 向量库 |
| `src/core/SkFDot6.h` | 定点数定义 |
| `src/core/SkDraw.cpp` | 主要调用者 |
