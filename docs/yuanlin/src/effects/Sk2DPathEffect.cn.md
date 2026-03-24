# Sk2DPathEffect

> 源文件: include/effects/Sk2DPathEffect.h, src/effects/Sk2DPathEffect.cpp

## 概述

Sk2DPathEffect 是 Skia 中用于实现 2D 图案填充路径效果的模块。该模块提供了两个具体实现: SkLine2DPathEffect（线条图案）和 SkPath2DPathEffect（路径图案）。它通过矩阵变换将路径映射到整数网格,然后在每个网格点或跨度上重复绘制指定的图案元素,实现类似印章或纹理的填充效果。核心机制是路径栅格化 + 图案重复,常用于创建点阵、网格线和自定义填充纹理。

## 架构位置

Sk2DPathEffect 位于 Skia 的效果层路径效果子系统:

```
include/effects/
  └── Sk2DPathEffect.h         # 公共接口
src/effects/
  └── Sk2DPathEffect.cpp       # 实现（本模块）
src/core/
  ├── SkPathEffect.h            # 路径效果基类
  └── SkPathEffectBase.h        # 内部基类
```

该模块为客户端提供高级图案填充能力。

## 主要类与结构体

### 公共接口类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkLine2DPathEffect` | 无（工厂类） | 无 | 创建线条图案效果 |
| `SkPath2DPathEffect` | 无（工厂类） | 无 | 创建路径图案效果 |

### 内部实现类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `Sk2DPathEffect` | `SkPathEffectBase` | `SkMatrix fMatrix`<br>`SkMatrix fInverse`<br>`bool fMatrixIsInvertible` | 2D 效果抽象基类 |
| `SkLine2DPathEffectImpl` | `Sk2DPathEffect` | `SkScalar fWidth` | 线条图案实现 |
| `SkPath2DPathEffectImpl` | `Sk2DPathEffect` | `SkPath fPath` | 路径图案实现 |

## 公共 API 函数

### 工厂方法

```cpp
class SK_API SkLine2DPathEffect {
    // 创建线条图案: 在每个整数 y 坐标的连续 x 跨度上绘制线条
    static sk_sp<SkPathEffect> Make(SkScalar width, const SkMatrix& matrix);

    static void RegisterFlattenables();
};

class SK_API SkPath2DPathEffect {
    // 创建路径图案: 在每个网格点上放置指定路径
    static sk_sp<SkPathEffect> Make(const SkMatrix& matrix, const SkPath& path);

    static void RegisterFlattenables();
};
```

### 参数说明

**SkLine2DPathEffect::Make**
- `width`: 线条宽度（通过 SkStrokeRec 设置）
- `matrix`: 从像素空间到网格空间的变换矩阵
- 返回: 失败返回 nullptr（如 width < 0）

**SkPath2DPathEffect::Make**
- `matrix`: 从像素空间到网格空间的变换矩阵
- `path`: 要重复绘制的路径图案
- 返回: `sk_sp<SkPathEffect>` 智能指针

## 内部实现细节

### 核心算法流程

**onFilterPath 主流程** (Sk2DPathEffect):

```cpp
bool onFilterPath(SkPathBuilder* dst, const SkPath& src, ...) {
    if (!fMatrixIsInvertible) return false;

    // 1. 将路径变换到网格空间
    SkPath tmp = src.makeTransform(fInverse);

    // 2. 计算路径的整数边界
    SkIRect ir = tmp.getBounds().round();
    if (ir.isEmpty()) return true;

    this->begin(ir, dst);  // 子类初始化

    // 3. 栅格化路径为区域
    SkRegion rgn;
    rgn.setPath(tmp, SkRegion(ir));

    // 4. 遍历区域中的矩形
    SkRegion::Iterator iter(rgn);
    for (; !iter.done(); iter.next()) {
        const SkIRect& rect = iter.rect();

        // 5. 按行扫描
        for (int y = rect.fTop; y < rect.fBottom; ++y) {
            this->nextSpan(rect.fLeft, y, rect.width(), dst);
        }
    }

    this->end(dst);  // 子类清理
    return true;
}
```

### 模板方法模式

**虚函数接口**:
```cpp
virtual void begin(const SkIRect& uvBounds, SkPathBuilder* dst) const {}
virtual void next(const SkPoint& loc, int u, int v, SkPathBuilder* dst) const {}
virtual void end(SkPathBuilder* dst) const {}

virtual void nextSpan(int x, int y, int ucount, SkPathBuilder* builder) const {
    // 默认实现: 逐点调用 next()
    SkPoint src, dst;
    src.set(SkIntToScalar(x) + SK_ScalarHalf, SkIntToScalar(y) + SK_ScalarHalf);
    do {
        dst = fMatrix.mapPoint(src);
        this->next(dst, x++, y, builder);
        src.fX += SK_Scalar1;
    } while (--ucount > 0);
}
```

### SkLine2DPathEffectImpl 实现

**重写 nextSpan**:
```cpp
void nextSpan(int u, int v, int ucount, SkPathBuilder* dst) const override {
    if (ucount > 1) {
        SkPoint src[2], dstP[2];

        // 起点和终点
        src[0].set(SkIntToScalar(u) + SK_ScalarHalf,
                   SkIntToScalar(v) + SK_ScalarHalf);
        src[1].set(SkIntToScalar(u+ucount) + SK_ScalarHalf,
                   SkIntToScalar(v) + SK_ScalarHalf);

        // 变换回像素空间
        this->getMatrix().mapPoints(dstP, src);

        // 绘制线段
        dst->moveTo(dstP[0]);
        dst->lineTo(dstP[1]);
    }
}

bool onFilterPath(...) override {
    if (this->INHERITED::onFilterPath(dst, src, rec, cullRect, ctm)) {
        rec->setStrokeStyle(fWidth);  // 设置线条宽度
        return true;
    }
    return false;
}
```

特点: 优化为跨度级线条,避免逐点绘制

### SkPath2DPathEffectImpl 实现

**重写 next**:
```cpp
void next(const SkPoint& loc, int u, int v, SkPathBuilder* dst) const override {
    dst->addPath(fPath, loc.fX, loc.fY);  // 在每个网格点复制路径
}
```

特点: 简单复制路径到每个位置

### 矩阵处理

**构造函数初始化**:
```cpp
Sk2DPathEffect(const SkMatrix& mat) : fMatrix(mat) {
    // 预计算逆矩阵并设置类型掩码（线程安全）
    fMatrixIsInvertible = fMatrix.invert(&fInverse);
}
```

**坐标系统**:
- `fMatrix`: 网格空间 → 像素空间
- `fInverse`: 像素空间 → 网格空间（用于路径变换）

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkMatrix.h` | 坐标变换 |
| `include/core/SkPath.h` | 路径数据结构 |
| `include/core/SkPathBuilder.h` | 路径构建 |
| `include/core/SkRegion.h` | 路径栅格化 |
| `include/core/SkStrokeRec.h` | 笔画参数 |
| `src/core/SkPathEffectBase.h` | 基类实现 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| 客户端绘图代码 | 创建图案填充效果 |
| `SkPaint` | 应用路径效果 |
| 序列化系统 | 保存/加载效果 |

## 设计模式与设计决策

### 模板方法模式

**决策**: Sk2DPathEffect 提供算法骨架,子类实现具体步骤

```cpp
// 算法骨架
onFilterPath() {
    transform_path();
    rasterize_to_region();
    for each rectangle:
        for each row:
            nextSpan();  // 子类实现
}
```

**优点**:
- 复用栅格化逻辑
- 灵活的图案定义
- 易于扩展新图案类型

### 分层优化策略

**三个抽象层次**:
1. **点级** (`next`): 最大灵活性
2. **跨度级** (`nextSpan`): 中等优化（线条图案使用）
3. **区域级** (`begin/end`): 最大优化潜力（未充分利用）

### Fuzzer 安全性

**循环保护**:
```cpp
#if defined(SK_BUILD_FOR_FUZZER)
    if (ucount > 100) {
        return;  // 防止无限循环
    }
    if (rect.height() > 100) {
        continue;  // 跳过过大的矩形
    }
#endif
```

原因: 防止模糊测试中的资源耗尽攻击

## 性能考量

### 栅格化开销

**SkRegion::setPath**:
- 将路径转换为整数坐标矩形列表
- 开销: O(路径复杂度)
- 优化: 缓存区域结果（当前未实现）

### 跨度级优化

**SkLine2DPathEffectImpl**:
```cpp
// 避免
for (int x = left; x < right; ++x) {
    draw_point(x, y);
}

// 优化为
draw_line(left, y, right, y);
```

性能提升: ~10x（减少路径操作数量）

### 矩阵计算

**预计算逆矩阵**:
```cpp
fMatrixIsInvertible = fMatrix.invert(&fInverse);
```
- 构造时计算一次
- 避免重复求逆
- 支持快速失败

### 边界计算

```cpp
bool computeFastBounds(SkRect*) const override {
    return false;  // 假设无法计算（保守策略）
}
```

原因: 图案可能扩展到任意范围,精确计算成本高

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkPathEffect.h` | 依赖 | 路径效果基类 |
| `include/core/SkMatrix.h` | 依赖 | 矩阵变换 |
| `include/core/SkRegion.h` | 依赖 | 路径栅格化 |
| `include/effects/SkDashPathEffect.h` | 相关 | 另一种路径效果 |
| `src/core/SkPaint.cpp` | 使用者 | 应用效果 |
