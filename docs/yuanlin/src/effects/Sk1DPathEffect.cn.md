# Sk1DPathEffect

> 源文件: include/effects/Sk1DPathEffect.h, src/effects/Sk1DPathEffect.cpp

## 概述

Sk1DPathEffect 是 Skia 中用于沿路径重复绘制图案的一维路径效果模块。该模块通过 SkPath1DPathEffect 实现沿路径"印章"功能,支持三种变换样式: 平移（Translate）、旋转（Rotate）和变形（Morph）。它使用 SkPathMeasure 测量路径长度并计算图案放置位置,通过相位参数控制起始偏移,通过前进距离参数控制图案间隔。常用于创建虚线、路径装饰和动态图案效果。

## 架构位置

Sk1DPathEffect 位于 Skia 的效果层路径效果子系统:

```
include/effects/
  └── Sk1DPathEffect.h          # 公共接口
src/effects/
  └── Sk1DPathEffect.cpp        # 实现（本模块）
src/core/
  ├── SkPathEffect.h             # 路径效果基类
  └── SkPathEffectBase.h         # 内部基类
```

该模块为客户端提供路径装饰和动画效果。

## 主要类与结构体

### 公共接口类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkPath1DPathEffect` | 无（工厂类） | 无 | 提供静态工厂方法和枚举 |

#### Style 枚举

| 枚举值 | 说明 |
|--------|------|
| `kTranslate_Style` | 将图案平移到每个位置 |
| `kRotate_Style` | 围绕图案中心旋转 |
| `kMorph_Style` | 变形每个点,将直线转换为曲线 |

### 内部实现类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `Sk1DPathEffect` | `SkPathEffectBase` | 无 | 一维效果抽象基类 |
| `SkPath1DPathEffectImpl` | `Sk1DPathEffect` | `SkPath fPath`<br>`SkScalar fAdvance`<br>`SkScalar fInitialOffset`<br>`Style fStyle` | 具体实现类 |

## 公共 API 函数

### 工厂方法

```cpp
class SK_API SkPath1DPathEffect {
    enum Style {
        kTranslate_Style,   // 平移
        kRotate_Style,      // 旋转
        kMorph_Style,       // 变形
        kLastEnum_Style = kMorph_Style,
    };

    // 创建沿路径重复的图案效果
    static sk_sp<SkPathEffect> Make(
        const SkPath& path,    // 要重复的路径图案
        SkScalar advance,      // 图案间隔距离
        SkScalar phase,        // 初始相位偏移
        Style style            // 变换样式
    );

    static void RegisterFlattenables();
};
```

### 参数说明

**Make**
- `path`: 要重复绘制的路径图案（不能为空）
- `advance`: 沿路径的前进距离（必须 > 0）
- `phase`: 沿路径的初始偏移（模 advance）
  - 正值: 向前偏移
  - 负值: 向后偏移（自动转换为正值）
- `style`: 变换样式
- 返回: 失败返回 nullptr（参数无效时）

## 内部实现细节

### 相位处理

**构造函数中的相位规范化**:
```cpp
SkPath1DPathEffectImpl(..., SkScalar phase, Style style) {
    // 反转相位以匹配 PostScript 语义
    if (phase < 0) {
        phase = -phase;
        if (phase > advance) {
            phase = SkScalarMod(phase, advance);
        }
    } else {
        if (phase > advance) {
            phase = SkScalarMod(phase, advance);
        }
        phase = advance - phase;  // 反转
    }

    // 处理边界情况
    if (phase >= advance) {
        phase = 0;
    }

    fInitialOffset = phase;
}
```

语义: 相位作为沿路径的偏移量,转换为距离起点的距离

### 核心算法流程

**onFilterPath 实现** (Sk1DPathEffect):
```cpp
bool onFilterPath(SkPathBuilder* builder, const SkPath& src, ...) {
    SkPathMeasure meas(src, false);
    do {
        int governor = MAX_REASONABLE_ITERATIONS;  // 100000
        SkScalar length = meas.getLength();
        SkScalar distance = this->begin(length);  // 获取起始距离

        while (distance < length && --governor >= 0) {
            SkScalar delta = this->next(builder, distance, meas);
            if (delta <= 0) {
                break;  // 子类返回 <= 0 表示停止
            }
            distance += delta;
        }

        if (governor < 0) {
            return false;  // 防止无限循环
        }
    } while (meas.nextContour());  // 处理多轮廓

    return true;
}
```

### 三种样式实现

**kTranslate_Style** (平移):
```cpp
case kTranslate_Style: {
    SkPoint pos;
    if (meas.getPosTan(distance, &pos, nullptr)) {
        builder->addPath(fPath, pos.fX, pos.fY);
    }
    break;
}
```

**kRotate_Style** (旋转):
```cpp
case kRotate_Style: {
    SkMatrix matrix;
    if (meas.getMatrix(distance, &matrix)) {
        // matrix 包含位置和切线方向
        builder->addPath(fPath, matrix);
    }
    break;
}
```

**kMorph_Style** (变形):
```cpp
case kMorph_Style:
    morphpath(builder, fPath, meas, distance);
    break;
```

### 变形算法详解

**morphpoints 函数**:
```cpp
static bool morphpoints(SkSpan<SkPoint> dst, SkSpan<const SkPoint> src,
                        SkPathMeasure& meas, SkScalar dist) {
    for (size_t i = 0; i < src.size(); i++) {
        SkPoint pos;
        SkVector tangent;
        SkScalar sx = src[i].fX;
        SkScalar sy = src[i].fY;

        // 获取路径上的位置和切线
        if (!meas.getPosTan(dist + sx, &pos, &tangent)) {
            return false;
        }

        // 构建变换矩阵: 旋转 + 平移
        SkMatrix matrix;
        matrix.setSinCos(tangent.fY, tangent.fX, 0, 0);
        matrix.preTranslate(-sx, 0);   // 移动到原点
        matrix.postTranslate(pos.fX, pos.fY);  // 移动到目标位置

        dst[i] = matrix.mapPoint(SkPoint{sx, sy});
    }
    return true;
}
```

**morphpath 函数**:
```cpp
static void morphpath(SkPathBuilder* dst, const SkPath& src,
                      SkPathMeasure& meas, SkScalar dist) {
    SkPath::Iter iter(src, false);
    SkPoint dstP[3], scratch[3];

    while (auto rec = iter.next()) {
        switch (rec->fVerb) {
            case SkPathVerb::kLine:
                // 将线段转换为二次曲线以更好地拟合
                scratch[0] = srcP[0];
                scratch[1].set(sk_float_midpoint(srcP[0].fX, srcP[1].fX),
                               sk_float_midpoint(srcP[0].fY, srcP[1].fY));
                scratch[2] = srcP[1];
                // 变形并绘制为 quadTo
                morphpoints(dstP, scratch.subspan(1), meas, dist);
                dst->quadTo(dstP[0], dstP[1]);
                break;

            case SkPathVerb::kQuad:
            case SkPathVerb::kConic:
            case SkPathVerb::kCubic:
                // 变形控制点
                morphpoints(dstP, srcP.subspan(1), meas, dist);
                dst->quadTo/conicTo/cubicTo(...);
                break;
        }
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkPathEffect.h` | 路径效果基类 |
| `include/core/SkPathMeasure.h` | 路径测量 |
| `include/core/SkPath.h` | 路径数据结构 |
| `include/core/SkPathBuilder.h` | 路径构建 |
| `include/core/SkMatrix.h` | 坐标变换 |
| `include/core/SkStrokeRec.h` | 笔画记录 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| 客户端绘图代码 | 创建路径装饰效果 |
| `SkPaint` | 应用路径效果 |
| 动画系统 | 动态调整相位参数 |

## 设计模式与设计决策

### 模板方法模式

**决策**: Sk1DPathEffect 提供算法骨架,子类实现图案放置

```cpp
// 抽象基类定义流程
class Sk1DPathEffect {
    virtual SkScalar begin(SkScalar contourLength) const = 0;
    virtual SkScalar next(SkPathBuilder*, SkScalar, SkPathMeasure&) const = 0;
};

// 具体实现
class SkPath1DPathEffectImpl : public Sk1DPathEffect {
    SkScalar begin(...) const override {
        return fInitialOffset;  // 返回起始距离
    }

    SkScalar next(...) const override {
        // 根据样式绘制图案
        switch (fStyle) { ... }
        return fAdvance;  // 返回前进距离
    }
};
```

### 策略模式

**三种变换策略**:
- **平移**: 最简单,仅改变位置
- **旋转**: 中等复杂度,匹配路径切线
- **变形**: 最复杂,变形图案以贴合路径

选择标准: 根据视觉需求和性能考虑

### 性能保护

**循环治理器**:
```cpp
#define MAX_REASONABLE_ITERATIONS 100000

int governor = MAX_REASONABLE_ITERATIONS;
while (...&& --governor >= 0) {
    ...
}
if (governor < 0) {
    return false;  // 防止挂起
}
```

**Fuzzer 特殊处理**:
```cpp
#if defined(SK_BUILD_FOR_FUZZER)
    if (builder->countPoints() > 100000) {
        return fAdvance;  // 限制输出大小
    }
#endif
```

## 性能考量

### SkPathMeasure 开销

**getPosTan 调用**:
- 每次图案放置调用一次
- 涉及路径细分和查找
- 建议: 缓存测量结果（当前未实现）

### 变形算法复杂度

**morphpoints**:
- 每个点调用一次 `getPosTan`
- 矩阵构建和点变换
- 复杂度: O(图案点数)

**优化策略**:
- 减少图案复杂度
- 使用 kRotate_Style 代替 kMorph_Style

### 内存分配

```cpp
SkPath1DPathEffectImpl(...) {
    fPath = path;
    // 预计算边界缓存（线程安全）
    fPath.updateBoundsCache();
    (void)fPath.getGenerationID();
}
```

优点: 避免运行时边界计算

### 线段到曲线转换

```cpp
case SkPathVerb::kLine:
    scratch[1].set(sk_float_midpoint(srcP[0].fX, srcP[1].fX),
                   sk_float_midpoint(srcP[0].fY, srcP[1].fY));
```

原因: 曲线更好地拟合弯曲路径

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkPathEffect.h` | 依赖 | 路径效果基类 |
| `include/core/SkPathMeasure.h` | 依赖 | 路径测量工具 |
| `include/core/SkPath.h` | 依赖 | 路径结构 |
| `include/effects/SkDashPathEffect.h` | 相关 | 虚线效果 |
| `include/effects/Sk2DPathEffect.h` | 相关 | 2D 图案效果 |
| `src/core/SkPaint.cpp` | 使用者 | 应用效果 |
