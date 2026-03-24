# GrClip

> 源文件
> - src/gpu/ganesh/GrClip.h

## 概述

`GrClip` 是 Ganesh GPU 后端中用于应用裁剪（clipping）的抽象基类。它定义了裁剪系统的接口，负责在绘制操作执行前确定哪些像素应该被绘制、哪些应该被裁剪掉。该类可以构建裁剪遮罩（clip mask），并填充 `GrAppliedClip` 结构来指导绘制状态的设置。

`GrHardClip` 是 `GrClip` 的一个特化子类，专门用于不使用覆盖片段处理器（coverage FPs）的硬件裁剪。它只能通过现有的模板缓冲区内容和/或固定功能状态（如剪刀矩形）来实现裁剪。

该文件还定义了重要的裁剪效果枚举、预裁剪结果结构，以及一系列用于像素边界计算和裁剪测试的静态工具函数。这些工具确保了裁剪在各种抗锯齿模式下都能正确工作。

## 架构位置

在 Skia 的 Ganesh GPU 渲染架构中，`GrClip` 位于绘制管线的前端：

```
绘制管线
    ├── GrDrawOp (绘制操作)
    ├── GrClip (裁剪抽象)
    │   ├── GrHardClip (硬件裁剪)
    │   └── GrClipStack (裁剪栈)
    ├── GrAppliedClip (应用的裁剪)
    │   ├── GrAppliedHardClip (硬件裁剪状态)
    │   └── GrCoverageFragmentProcessor (覆盖 FP)
    └── GrPipeline (渲染管线)
```

裁剪系统在操作执行前评估，将裁剪信息转换为 GPU 状态（剪刀、模板）或覆盖片段处理器。

## 主要类与结构体

### GrClip

抽象基类，定义裁剪接口。

**继承关系：** 纯虚基类，无继承自其他类。

**关键枚举类型：**

#### Effect

```cpp
enum class Effect {
    kClipped,      // 裁剪保守地修改绘制覆盖但不消除绘制
    kUnclipped,    // 裁剪确定不修改绘制覆盖
    kClippedOut    // 裁剪确定消除所有绘制覆盖
};
```

**关键结构体：**

#### PreClipResult

```cpp
struct PreClipResult {
    Effect  fEffect;
    SkRRect fRRect;     // 当 isRRect 为 false 时忽略
    GrAA    fAA;        // 当 isRRect 为 false 时忽略
    bool    fIsRRect;
};
```

该结构体封装了预裁剪分析的结果，可以描述简单的圆角矩形裁剪或更复杂的效果。

### GrHardClip

硬件裁剪的具体基类。

**继承关系：**
```
GrClip (基类)
    └── GrHardClip
```

该类特化了 `apply()` 方法，只处理硬件状态（剪刀、模板），不使用覆盖片段处理器。

## 公共 API 函数

### GrClip 核心接口

#### 保守边界查询

```cpp
virtual SkIRect getConservativeBounds() const = 0;
```

**功能：** 计算限制在给定渲染目标尺寸内的保守像素边界。

返回的边界表示可以绘制的像素限制；边界外的任何内容都将完全被裁剪。

#### 应用裁剪

```cpp
virtual Effect apply(GrRecordingContext* context,
                     skgpu::ganesh::SurfaceDrawContext* sdc,
                     GrDrawOp* op,
                     GrAAType aa,
                     GrAppliedClip* out,
                     SkRect* bounds) const = 0;
```

**功能：** 计算应用的裁剪信息，用于构建 `GrPipeline`。

**参数：**
- `context`: 录制上下文
- `sdc`: 表面绘制上下文
- `op`: 要裁剪的绘制操作
- `aa`: 抗锯齿类型
- `out`: 输出的应用裁剪
- `bounds`: 输入/输出的绘制边界

**返回值：**
- `kClipped`: 边界已更新以包含在裁剪内
- `kUnclipped`: 边界已更新（或保持不变）
- `kClippedOut`: 边界和裁剪处于未定义状态，应跳过绘制

#### 预裁剪分析

```cpp
virtual PreClipResult preApply(const SkRect& drawBounds, GrAA aa) const;
```

**功能：** 对绘制边界进行初步的保守分析。

默认实现检查绘制边界是否与保守边界相交：
```cpp
SkIRect pixelBounds = GetPixelIBounds(drawBounds, aa);
bool outside = !SkIRect::Intersects(pixelBounds, this->getConservativeBounds());
return outside ? Effect::kClippedOut : Effect::kClipped;
```

子类可以返回更精确的结果，特别是当裁剪可以表示为单个圆角矩形时。

### GrHardClip 接口

```cpp
virtual Effect apply(GrAppliedHardClip* out, SkIRect* bounds) const = 0;
```

**功能：** 设置适当的硬件状态修改来实现裁剪。

该方法是纯虚的，由具体的硬件裁剪实现（如剪刀裁剪、模板裁剪）提供。

### 静态工具函数

#### 内部/外部裁剪测试

```cpp
static bool IsInsideClip(const SkIRect& innerClipBounds, const SkRect& drawBounds, GrAA aa);
static bool IsOutsideClip(const SkIRect& outerClipBounds, const SkRect& drawBounds, GrAA aa);
```

**功能：** 判断绘制边界是否完全在裁剪内部或外部。

这些快速测试用于优化绘制提交，避免不必要的裁剪计算。

#### 像素边界计算

```cpp
enum class BoundsType {
    kExterior,  // 返回包含所有可能非零覆盖的像素的最小边界
    kInterior   // 返回保证完全覆盖的最大边界
};

static SkIRect GetPixelIBounds(const SkRect& bounds, GrAA aa,
                               BoundsType mode = BoundsType::kExterior);
```

**功能：** 将解析几何边界转换为整数像素边界。

该函数根据抗锯齿类型和边界模式进行不同的舍入：

**kExterior 模式（默认）：**
- 非 AA：使用容差舍入到最近整数
- AA：向外取整（floor/ceil）

**kInterior 模式：**
- 非 AA：使用容差舍入到最近整数
- AA：向内取整（ceil/floor）

**实现细节：**
```cpp
auto roundLow = [aa](float v) {
    v += kBoundsTolerance;
    return aa == GrAA::kNo ? SkScalarRoundToInt(v - kHalfPixelRoundingTolerance)
                           : SkScalarFloorToInt(v);
};
auto roundHigh = [aa](float v) {
    v -= kBoundsTolerance;
    return aa == GrAA::kNo ? SkScalarRoundToInt(v + kHalfPixelRoundingTolerance)
                           : SkScalarCeilToInt(v);
};
```

#### 像素对齐检测

```cpp
static bool IsPixelAligned(const SkRect& rect);
```

**功能：** 判断矩形是否与像素边界对齐。

使用 `kBoundsTolerance` 容差，允许浮点舍入误差。

## 内部实现细节

### 容差常量

```cpp
constexpr static SkScalar kBoundsTolerance = 1e-3f;
constexpr static SkScalar kHalfPixelRoundingTolerance = 5e-2f;
```

**kBoundsTolerance：** 允许绘制扩展到裁剪边界之外的最大距离。这是为了容忍浮点舍入误差。在覆盖情况下，只要覆盖保持在其预期值的 0.5/256 之内，就不应该影响最终像素值。

**kHalfPixelRoundingTolerance：** 半像素顶点坐标的容差，用于处理 GPU 光栅化器的不一致舍入。GPU 规范未定义舍入方法，光栅化器精度经常导致小于 1/2 的分数仍然向上舍入。对于非 AA 边界边缘，0.45 到 0.55 之间的值可能向内或向外舍入，取决于其所在的边。

### GrHardClip 的 apply 实现

```cpp
Effect apply(GrRecordingContext*,
             skgpu::ganesh::SurfaceDrawContext*,
             GrDrawOp*,
             GrAAType aa,
             GrAppliedClip* out,
             SkRect* bounds) const final {
    SkIRect pixelBounds = GetPixelIBounds(*bounds, GrAA(aa != GrAAType::kNone));
    Effect effect = this->apply(&out->hardClip(), &pixelBounds);
    bounds->intersect(SkRect::Make(pixelBounds));
    return effect;
}
```

该实现：
1. 将浮点边界转换为像素边界
2. 调用子类的硬件裁剪实现
3. 将边界与裁剪后的像素边界相交
4. 返回效果

这确保了硬件裁剪始终正确地更新边界。

### 抗锯齿舍入逻辑

非 AA 和 AA 的舍入策略不同：

**非 AA：** 使用 `round()` 并带有容差，因为 GPU 会将顶点舍入到最近的像素中心。

**AA：** 使用 `floor()`/`ceil()`，因为抗锯齿会在边缘产生部分覆盖，需要包含所有可能被部分覆盖的像素。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRRect` | 圆角矩形，用于表示常见的裁剪形状 |
| `SkRect` | 矩形类型 |
| `SkScalar` | 浮点数类型 |
| `GrTypesPriv` | GPU 类型定义（如 `GrAA`, `GrAAType`） |
| `GrAppliedClip` | 应用的裁剪结果 |
| `GrDrawOp` | 绘制操作 |
| `GrRecordingContext` | 录制上下文 |
| `skgpu::ganesh::SurfaceDrawContext` | 表面绘制上下文 |

### 被依赖的模块

`GrClip` 被广泛使用于：

| 模块 | 使用方式 |
|------|---------|
| `GrDrawOp` | 所有绘制操作都需要考虑裁剪 |
| `GrClipStack` | 实现具体的裁剪栈 |
| `GrClipStackClip` | 基于裁剪栈的裁剪实现 |
| `GrReducedClip` | 优化的裁剪表示 |
| `SurfaceDrawContext` | 在绘制时应用裁剪 |
| `GrFixedClip` | 简单的固定裁剪实现 |

## 设计模式与设计决策

### 策略模式

`GrClip` 使用策略模式，允许不同的裁剪策略（硬件裁剪、覆盖裁剪、混合裁剪）通过统一的接口使用。

### 模板方法模式

`GrHardClip` 使用模板方法模式，定义了 `apply()` 的骨架算法，将具体的硬件状态设置委托给子类。

### 两阶段裁剪检测

设计采用两阶段方法：
1. **preApply()**: 快速、保守的分析
2. **apply()**: 完整、可能昂贵的裁剪应用

这允许在绘制提交前进行早期剔除，避免不必要的工作。

### 容差驱动的几何处理

使用明确定义的容差（`kBoundsTolerance`, `kHalfPixelRoundingTolerance`）处理浮点不精确性和 GPU 行为的不确定性。这是图形编程中的关键技术。

### 边界传播

`apply()` 方法修改边界参数，将其与裁剪相交。这种设计允许绘制系统逐步细化边界，从保守估计到精确边界。

### Effect 枚举

使用枚举而非布尔值表示三种可能的裁剪结果，使代码更清晰且易于扩展。

## 性能考量

### 早期剔除

`preApply()` 和 `IsOutsideClip()` 允许在昂贵的裁剪计算前快速识别完全被裁剪的绘制。

### 避免不必要的裁剪

通过返回 `Effect::kUnclipped`，系统可以跳过裁剪状态设置，减少 GPU 状态更改。

### 硬件裁剪优化

`GrHardClip` 避免使用覆盖片段处理器，这比软件裁剪更快：
- 剪刀测试：几乎零开销
- 模板测试：较低开销，但需要模板缓冲区

### 圆角矩形特化

`PreClipResult` 可以表示圆角矩形裁剪，允许特殊的快速路径：
- 某些 GPU 有硬件圆角矩形支持
- 可以生成优化的片段着色器代码

### 像素边界缓存

`GetPixelIBounds()` 的结果通常被缓存，避免重复计算。

### 容差优化

使用容差允许更激进的优化，例如将"几乎对齐"的边界视为对齐，从而使用更快的代码路径。

### 内联 lambda 表达式

`GetPixelIBounds()` 中使用 lambda 表达式定义舍入函数，编译器可以内联这些函数，避免函数调用开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrAppliedClip.h` | 依赖 | 定义应用裁剪的结果 |
| `src/gpu/ganesh/GrDrawOp.h` | 依赖 | 绘制操作接口 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | GPU 私有类型 |
| `include/core/SkRRect.h` | 依赖 | 圆角矩形 |
| `src/gpu/ganesh/GrClipStack.h` | 实现 | 裁剪栈实现 |
| `src/gpu/ganesh/GrClipStackClip.h` | 实现 | 基于栈的裁剪 |
| `src/gpu/ganesh/GrFixedClip.h` | 实现 | 固定裁剪实现 |
| `src/gpu/ganesh/GrReducedClip.h` | 实现 | 优化的裁剪 |
| `src/gpu/ganesh/v1/SurfaceDrawContext.h` | 使用者 | 应用裁剪到绘制 |
