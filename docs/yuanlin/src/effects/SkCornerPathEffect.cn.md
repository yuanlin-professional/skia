# SkCornerPathEffect

> 源文件: include/effects/SkCornerPathEffect.h, src/effects/SkCornerPathEffect.cpp

## 概述

SkCornerPathEffect 是 Skia 中用于将路径尖锐拐角转换为圆角的路径效果类。该模块通过指定圆角半径,自动将路径中的直线段连接处转换为平滑的二次贝塞尔曲线,实现路径的圆角化处理。它主要处理直线段（kLine）,对于曲线段（kQuad、kConic、kCubic）则保持原样,是 Skia 路径效果系统中最常用的基础效果之一。

## 架构位置

SkCornerPathEffect 位于 Skia 的效果层路径效果子系统:

```
include/effects/
  └── SkCornerPathEffect.h     # 公共接口
src/effects/
  └── SkCornerPathEffect.cpp   # 实现（本模块）
src/core/
  ├── SkPathEffect.h            # 路径效果基类
  └── SkPathEffectBase.h        # 内部基类
```

该模块属于客户端 API,用于 2D 图形绘制中的路径装饰。

## 主要类与结构体

### 公共接口类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkCornerPathEffect` | 无（工厂类） | 无 | 提供静态工厂方法 |

### 内部实现类

| 类名 | 继承关系 | 关键成员变量 | 说明 |
|------|---------|------------|------|
| `SkCornerPathEffectImpl` | `SkPathEffectBase` | `SkScalar fRadius` | 实际效果实现类 |

## 公共 API 函数

### 工厂方法

```cpp
class SkCornerPathEffect {
    // 创建圆角效果
    static sk_sp<SkPathEffect> Make(SkScalar radius);

    // 注册序列化支持
    static void RegisterFlattenables();
};
```

### 参数说明

**Make**
- `radius`: 圆角半径（必须 > 0 才有效果）
  - 指定从每个拐角向两端延伸的距离
  - 超过线段长度一半时会自动调整
- 返回: `sk_sp<SkPathEffect>` 智能指针,失败返回 nullptr

## 内部实现细节

### 核心算法

#### ComputeStep 函数

```cpp
static bool ComputeStep(const SkPoint& a, const SkPoint& b,
                        SkScalar radius, SkPoint* step)
{
    SkScalar dist = SkPoint::Distance(a, b);

    *step = b - a;
    if (dist <= radius * 2) {
        *step *= SK_ScalarHalf;  // 线段过短,使用中点
        return false;
    } else {
        *step *= radius / dist;   // 标准化为单位向量后缩放
        return true;
    }
}
```

功能:
- 计算从顶点向线段方向的偏移向量
- 处理线段长度不足 2*radius 的情况
- 返回是否需要绘制中间直线段

### 路径过滤实现

**onFilterPath 主流程**:

```cpp
bool onFilterPath(SkPathBuilder* dst, const SkPath& src, ...) {
    SkPath::Iter iter(src, false);
    SkPoint moveTo, lastCorner;
    SkVector firstStep, step;
    bool closed, prevIsValid = true;

    while (auto rec = iter.next()) {
        switch (rec->fVerb) {
            case SkPathVerb::kMove:
                // 处理 moveTo
                closed = iter.isClosedContour();
                if (closed) {
                    moveTo = pts[0];
                    prevIsValid = false;  // 延迟第一个 moveTo
                } else {
                    dst->moveTo(pts[0]);
                }
                break;

            case SkPathVerb::kLine:
                // 计算步进向量
                bool drawSegment = ComputeStep(pts[0], pts[1], fRadius, &step);

                // 绘制前一个拐角的圆弧
                if (!prevIsValid) {
                    dst->moveTo(moveTo + step);
                } else {
                    dst->quadTo(pts[0], pts[0] + step);
                }

                // 绘制中间直线
                if (drawSegment) {
                    dst->lineTo(pts[1] - step);
                }

                lastCorner = pts[1];
                break;

            case SkPathVerb::kQuad:
            case SkPathVerb::kConic:
            case SkPathVerb::kCubic:
                // 曲线段保持不变
                dst->quadTo/conicTo/cubicTo(...);
                break;

            case SkPathVerb::kClose:
                // 闭合路径时连接首尾
                if (firstStep.fX || firstStep.fY) {
                    dst->quadTo(lastCorner, lastCorner + firstStep);
                }
                dst->close();
                break;
        }
    }
}
```

### 圆角绘制策略

**标准情况** (线段长度 > 2*radius):
```
原始:  A ----------- B
               ↓
圆角化: A ----. ⌒ .---- B
         (quad)
```

**短线段情况** (线段长度 ≤ 2*radius):
```
原始:  A --- B
         ↓
圆角化: A .⌒. B
        (仅圆弧)
```

### 闭合路径处理

```cpp
// 记录第一个步进向量
if (SkPathVerb::kMove == prevVerb) {
    firstStep = step;
}

// kClose 时连接最后一个角和第一个角
if (firstStep.fX || firstStep.fY) {
    dst->quadTo(lastCorner, lastCorner + firstStep);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `include/core/SkPathEffect.h` | 路径效果基类 |
| `src/core/SkPathEffectBase.h` | 内部实现基类 |
| `include/core/SkPath.h` | 路径数据结构 |
| `include/core/SkPathBuilder.h` | 路径构建器 |
| `src/core/SkReadBuffer.h` | 反序列化 |
| `src/core/SkWriteBuffer.h` | 序列化 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| 客户端绘图代码 | 应用圆角效果到路径 |
| `SkPaint` | 作为 paint 的路径效果 |
| 序列化系统 | 保存/加载效果参数 |

## 设计模式与设计决策

### 工厂方法模式

**决策**: 通过静态 `Make` 方法创建实例,隐藏实现类

**优点**:
- 封装实现细节（SkCornerPathEffectImpl）
- 参数验证在工厂方法中完成
- 支持返回 nullptr 表示失败

```cpp
static sk_sp<SkPathEffect> Make(SkScalar radius) {
    return SkIsFinite(radius) && (radius > 0) ?
        sk_sp<SkPathEffect>(new SkCornerPathEffectImpl(radius)) : nullptr;
}
```

### 延迟初始化策略

**闭合路径的延迟 moveTo**:
```cpp
if (closed) {
    moveTo = pts[0];
    prevIsValid = false;  // 等到第一条线段时再 moveTo
} else {
    dst->moveTo(pts[0]);
}
```

**原因**: 闭合路径需要知道第一个步进向量才能正确放置起点

### 优雅降级

**曲线段处理**:
```cpp
case SkPathVerb::kQuad:
    // TBD - just replicate the curve for now
    dst->quadTo(pts[1], pts[2]);
    break;
```

设计决策: 暂时保持曲线不变,避免复杂的曲线分割逻辑

## 性能考量

### 计算优化

1. **向量计算复用**:
   ```cpp
   *step = b - a;
   *step *= radius / dist;  // 仅一次除法
   ```

2. **避免平方根**: 使用 `SkPoint::Distance` 但仅调用一次

3. **快速边界计算**:
   ```cpp
   bool computeFastBounds(SkRect*) const override {
       // 圆角化不改变边界
       return true;
   }
   ```

### 内存效率

- `fRadius` 单一浮点数成员（4 字节）
- 无额外堆分配
- 使用 SkPathBuilder 的栈缓冲

### 边界情况处理

**短线段**:
```cpp
if (dist <= radius * 2) {
    *step *= SK_ScalarHalf;  // 防止过度圆角化
}
```

**无效半径**:
```cpp
if (fRadius <= 0) {
    return false;  // 快速失败
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/core/SkPathEffect.h` | 依赖 | 路径效果基类 |
| `src/core/SkPathEffectBase.h` | 依赖 | 内部基类 |
| `include/core/SkPath.h` | 依赖 | 路径结构 |
| `include/core/SkPathBuilder.h` | 依赖 | 构建器 |
| `include/effects/SkDashPathEffect.h` | 相关 | 另一种路径效果 |
| `src/core/SkPaint.cpp` | 使用者 | 应用路径效果 |
