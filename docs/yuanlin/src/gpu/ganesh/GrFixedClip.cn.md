# GrFixedClip

> 源文件
> - src/gpu/ganesh/GrFixedClip.h
> - src/gpu/ganesh/GrFixedClip.cpp

## 概述

`GrFixedClip` 是 Skia Ganesh GPU 渲染后端中实现固定裁剪（硬件裁剪）的类。它使用剪刀测试（scissor test）和窗口矩形（window rectangles）来实现高效的硬件加速裁剪。与软件裁剪不同，GrFixedClip 直接利用 GPU 的硬件裁剪功能，避免了昂贵的模板缓冲区操作或片段着色器计算。

该类继承自 `GrHardClip`，提供了矩形边界裁剪和排除矩形裁剪两种功能。这种裁剪方式速度快，但功能相对受限，仅支持轴对齐的矩形区域。

## 架构位置

GrFixedClip 在 Ganesh 渲染管线中的位置：

```
SkCanvas (设置裁剪区域)
    ↓
SkDevice (转换裁剪)
    ↓
GrClip (裁剪抽象接口)
    ↓
GrFixedClip ← [硬件裁剪实现]
    ↓
GrAppliedHardClip (应用的裁剪状态)
    ↓
GrOpsTask/Pipeline (渲染管线)
    ↓
GPU 硬件 (剪刀测试、窗口矩形)
```

裁剪层次结构：
- `GrClip`：抽象基类
  - `GrHardClip`：硬件裁剪基类
    - `GrFixedClip`：固定矩形裁剪
  - `GrClipStack`：完整的裁剪栈（支持复杂形状）

## 主要类与结构体

### GrFixedClip 类

| 类型 | 说明 |
|------|------|
| **继承关系** | 继承自 `GrHardClip` (final 类) |
| **父类** | `GrHardClip` → `GrClip` |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fScissorState` | `GrScissorState` | 剪刀测试状态（矩形边界） |
| `fWindowRectsState` | `GrWindowRectsState` | 窗口矩形状态（排除区域） |

### 辅助类

**GrScissorState**
- 管理剪刀测试的矩形区域
- 支持启用/禁用状态
- 提供矩形交集操作

**GrWindowRectsState**
- 管理窗口矩形列表
- 支持包含/排除模式
- 用于在裁剪区域内排除特定矩形

## 公共 API 函数

### 构造函数

```cpp
// 仅指定渲染目标尺寸
explicit GrFixedClip(const SkISize& rtDims);

// 同时设置剪刀矩形
GrFixedClip(const SkISize& rtDims, const SkIRect& scissorRect);
```

### 剪刀测试管理

```cpp
// 获取剪刀状态
const GrScissorState& scissorState() const;
bool scissorEnabled() const;
const SkIRect& scissorRect() const;  // 返回剪刀矩形或 RT 边界

// 修改剪刀状态
void disableScissor();
[[nodiscard]] bool setScissor(const SkIRect& irect);
[[nodiscard]] bool intersect(const SkIRect& irect);  // 与现有矩形求交
```

### 窗口矩形管理

```cpp
// 获取窗口矩形状态
const GrWindowRectsState& windowRectsState() const;
bool hasWindowRectangles() const;

// 修改窗口矩形
void disableWindowRectangles();
void setWindowRectangles(
    const GrWindowRectangles& windows,
    GrWindowRectsState::Mode mode  // kInclusive 或 kExclusive
);
```

### 裁剪应用（继承自 GrClip）

```cpp
// 获取保守边界（最大可能影响的区域）
SkIRect getConservativeBounds() const final;

// 应用裁剪到硬件裁剪对象
Effect apply(GrAppliedHardClip*, SkIRect* drawBounds) const final;

// 预应用检查（在实际应用前快速判断）
PreClipResult preApply(const SkRect& drawBounds, GrAA aa) const final;
```

## 内部实现细节

### 剪刀测试实现

```cpp
const SkIRect& GrFixedClip::scissorRect() const {
    // 如果剪刀测试未启用，返回整个渲染目标边界
    return fScissorState.rect();
}

bool GrFixedClip::setScissor(const SkIRect& irect) {
    // 设置新的剪刀矩形
    // 返回 false 表示矩形无效或超出范围
    return fScissorState.set(irect);
}

bool GrFixedClip::intersect(const SkIRect& irect) {
    // 与现有剪刀矩形求交集
    // 返回 false 表示交集为空
    return fScissorState.intersect(irect);
}
```

### 保守边界计算

```cpp
SkIRect GrFixedClip::getConservativeBounds() const {
    // 返回剪刀矩形作为保守边界
    // 这是最简单的实现，因为固定裁剪总是矩形的
    return fScissorState.rect();
}
```

### 预应用优化

```cpp
GrClip::PreClipResult GrFixedClip::preApply(
    const SkRect& drawBounds,
    GrAA aa) const {

    // 1. 将绘制边界转换为像素整数边界
    SkIRect pixelBounds = GetPixelIBounds(drawBounds, aa);

    // 2. 检查是否完全被裁剪掉
    if (!SkIRect::Intersects(fScissorState.rect(), pixelBounds)) {
        return Effect::kClippedOut;  // 完全裁剪
    }

    // 3. 如果有窗口矩形，必须应用裁剪
    if (fWindowRectsState.enabled()) {
        return Effect::kClipped;
    }

    // 4. 检查剪刀矩形是否包含整个绘制区域
    if (!fScissorState.enabled() ||
        fScissorState.rect().contains(pixelBounds)) {
        return Effect::kUnclipped;  // 无需裁剪
    }

    // 5. 返回剪刀矩形作为退化的圆角矩形
    return {SkRect::Make(fScissorState.rect()), GrAA::kNo};
}
```

**优化要点**：
- 快速路径：完全裁剪和完全不裁剪的情况
- 避免不必要的硬件状态设置
- 将矩形裁剪表示为退化的抗锯齿圆角矩形

### 应用裁剪到硬件

```cpp
GrClip::Effect GrFixedClip::apply(
    GrAppliedHardClip* out,
    SkIRect* bounds) const {

    // 1. 检查绘制边界是否与剪刀矩形相交
    if (!SkIRect::Intersects(fScissorState.rect(), *bounds)) {
        return Effect::kClippedOut;
    }

    Effect effect = Effect::kUnclipped;

    // 2. 应用剪刀测试
    if (fScissorState.enabled() &&
        !fScissorState.rect().contains(*bounds)) {
        // 更新绘制边界为交集
        SkAssertResult(bounds->intersect(fScissorState.rect()));
        // 设置硬件剪刀状态
        out->setScissor(*bounds);
        effect = Effect::kClipped;
    }

    // 3. 添加窗口矩形
    if (fWindowRectsState.enabled()) {
        out->addWindowRectangles(fWindowRectsState);
        // 保守地假设有裁剪效果
        effect = Effect::kClipped;
    }

    return effect;
}
```

**关键步骤**：
1. 更新绘制边界到实际可见区域
2. 设置 GPU 剪刀状态
3. 添加窗口矩形到硬件状态
4. 返回裁剪效果类型

### 窗口矩形的作用

窗口矩形（Window Rectangles）是一种硬件特性，允许在剪刀矩形内排除（或仅包含）特定的子矩形：

```
Scissor Rect: [====================================]
Window Rects:      [xx]        [xx]       [xx]
Result:       [====    ========    =======    ====]
               (排除窗口矩形的区域)
```

**使用场景**：
- 复杂裁剪的近似
- 避免重绘已绘制的区域
- 优化图层混合

**限制**：
- 硬件支持有限（最多 8 个矩形）
- 只能是轴对齐的矩形
- 部分 GPU 不支持

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrClip` / `GrHardClip` | 基类定义 |
| `GrScissorState` | 管理剪刀测试状态 |
| `GrWindowRectsState` | 管理窗口矩形状态 |
| `GrAppliedHardClip` | 应用的裁剪结果 |
| `SkIRect` / `SkRect` | 矩形表示 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrRenderTargetContext` | 使用固定裁剪进行绘制 |
| `GrOpsTask` | 在操作任务中应用裁剪 |
| `GrPipeline` | 将裁剪状态传递给管线 |
| `GrOp` | 绘制操作使用裁剪 |

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）

GrFixedClip 是硬件裁剪策略的一种实现：

```
GrClip (策略接口)
    ↓
GrHardClip (硬件策略)
    ↓
GrFixedClip (固定矩形策略)
```

**优点**：
- 可以在运行时选择不同的裁剪策略
- 硬件裁剪 vs 模板裁剪 vs 混合裁剪

### 2. 不可变语义（部分）

```cpp
[[nodiscard]] bool setScissor(const SkIRect& irect);
[[nodiscard]] bool intersect(const SkIRect& irect);
```

使用 `[[nodiscard]]` 属性强制调用者检查返回值，确保：
- 检测裁剪失败（矩形为空）
- 避免静默错误

### 3. Final 类设计

```cpp
class GrFixedClip final : public GrHardClip { ... };
```

**决策**：将 GrFixedClip 标记为 final
- **原因**：这是最底层的实现，不需要进一步继承
- **优点**：编译器可以去虚化（devirtualization）优化

### 设计决策

**决策 1：使用硬件剪刀测试而非模板缓冲区**
- **优点**：速度快，无需额外内存
- **缺点**：只支持单个轴对齐矩形
- **适用场景**：大多数简单裁剪情况

**决策 2：支持窗口矩形**
- **原因**：扩展硬件裁剪能力
- **限制**：不是所有 GPU 都支持
- **降级策略**：在不支持时回退到其他裁剪方式

**决策 3：保守边界返回剪刀矩形**
- **原因**：固定裁剪总是矩形的，剪刀矩形就是精确边界
- **对比**：复杂裁剪可能返回更大的保守边界

**决策 4：PreClip 快速路径**
- **优化**：在实际应用前快速判断裁剪效果
- **收益**：避免不必要的状态设置和内存分配

## 性能考量

### 1. 硬件加速

剪刀测试是 GPU 的原生功能：
- **速度**：几乎零开销
- **对比**：模板测试需要额外的内存带宽和操作
- **适用**：所有轴对齐矩形裁剪

### 2. 早期剔除

```cpp
PreClipResult GrFixedClip::preApply(...) const {
    // 在绘制前检查是否完全裁剪
    if (!SkIRect::Intersects(fScissorState.rect(), pixelBounds)) {
        return Effect::kClippedOut;  // 避免提交绘制
    }
    // ...
}
```

**收益**：避免设置管线、分配资源等开销。

### 3. 状态最小化

```cpp
Effect GrFixedClip::apply(GrAppliedHardClip* out, SkIRect* bounds) const {
    // 只有在必要时才设置剪刀状态
    if (fScissorState.enabled() && !fScissorState.rect().contains(*bounds)) {
        out->setScissor(*bounds);
        effect = Effect::kClipped;
    }
}
```

**避免**：不必要的 GPU 状态更改。

### 4. 内存效率

```cpp
class GrFixedClip final : public GrHardClip {
    GrScissorState       fScissorState;       // ~16 bytes
    GrWindowRectsState   fWindowRectsState;   // ~small
};
```

**对比**：
- 模板缓冲区：width × height × N bytes per pixel
- 固定裁剪：常量大小（约 32-64 字节）

### 5. 窗口矩形限制

```cpp
// 硬件通常限制为 8 个窗口矩形
if (windowRects.count() > 8) {
    // 需要回退到其他裁剪方式
}
```

**注意**：检查 GPU 能力后使用。

### 6. 像素对齐优化

```cpp
SkIRect pixelBounds = GetPixelIBounds(drawBounds, aa);
```

**原因**：
- 剪刀测试工作在像素坐标
- 提前对齐避免精度问题

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/ganesh/GrClip.h` | 裁剪抽象基类 |
| `src/gpu/ganesh/GrHardClip.h` | 硬件裁剪基类 |
| `src/gpu/ganesh/GrScissorState.h` | 剪刀状态管理 |
| `src/gpu/ganesh/GrWindowRectsState.h` | 窗口矩形状态 |
| `src/gpu/ganesh/GrAppliedClip.h` | 应用的裁剪状态 |
| `src/gpu/ganesh/GrRenderTargetContext.h` | 使用裁剪的绘制上下文 |
| `src/gpu/ganesh/GrClipStack.h` | 完整的裁剪栈实现 |
| `src/gpu/ganesh/GrPipeline.h` | 渲染管线（使用裁剪） |
