# SkRasterClip

> 源文件: src/core/SkRasterClip.h, src/core/SkRasterClip.cpp

## 概述

`SkRasterClip` 是 Skia 中用于表示光栅化裁剪区域的核心类，它封装了 `SkRegion`（位图裁剪）和 `SkAAClip`（抗锯齿裁剪）两种裁剪方式，提供统一的接口来处理不同精度的裁剪操作。该类是 Skia 渲染管道中裁剪系统的关键组件，负责在像素级别精确控制绘制区域。

`SkRasterClip` 可以根据是否需要抗锯齿自动在两种内部表示之间切换，优化性能和内存使用。它还支持可选的着色器裁剪（shader clipping），用于实现更复杂的裁剪效果。

## 架构位置

`SkRasterClip` 位于 Skia 渲染管道的裁剪子系统中，是 `SkDevice` 和 `SkCanvas` 裁剪操作的底层实现基础。它在坐标变换后、像素填充前的阶段工作，将几何裁剪路径转换为像素级别的裁剪区域。

在架构层次上：
- **上层**：`SkCanvas` 提供用户级裁剪 API
- **中层**：`SkRasterClip` 处理光栅化裁剪逻辑
- **底层**：`SkRegion` 和 `SkAAClip` 提供具体的裁剪区域表示

## 主要类与结构体

### SkRasterClip 类

**继承关系：**
- 无继承关系（独立类）

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBW` | `SkRegion` | 位图裁剪区域（非抗锯齿） |
| `fAA` | `SkAAClip` | 抗锯齿裁剪区域 |
| `fIsBW` | `bool` | 当前是否使用位图模式 |
| `fIsEmpty` | `bool` | 缓存的空状态标志 |
| `fIsRect` | `bool` | 缓存的矩形状态标志 |
| `fShader` | `sk_sp<SkShader>` | 可选的着色器裁剪（增强裁剪而非替代） |

### SkAAClipBlitterWrapper 类

**继承关系：**
- 无继承关系（辅助类）

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBWRgn` | `SkRegion` | 临时位图区域 |
| `fAABlitter` | `SkAAClipBlitter` | 抗锯齿裁剪的 Blitter |
| `fClipRgn` | `const SkRegion*` | 返回给调用者的区域指针 |
| `fBlitter` | `SkBlitter*` | 返回给调用者的 Blitter 指针 |

### SkAutoRasterClipValidate 类

RAII（资源获取即初始化）辅助类，用于调试模式下自动验证 `SkRasterClip` 的状态。

## 公共 API 函数

### 构造与析构

```cpp
SkRasterClip();
explicit SkRasterClip(const SkIRect&);
explicit SkRasterClip(const SkRegion&);
explicit SkRasterClip(const SkRasterClip&);
SkRasterClip(const SkPath& path, const SkIRect& bounds, bool doAA);
~SkRasterClip();
```

提供多种构造方式，支持从矩形、区域、路径等创建裁剪对象。

### 状态查询

```cpp
bool isBW() const;
bool isAA() const;
bool isEmpty() const;
bool isRect() const;
bool isComplex() const;
const SkIRect& getBounds() const;
const SkRegion& bwRgn() const;
const SkAAClip& aaRgn() const;
```

查询裁剪区域的类型、状态和边界信息。

### 修改操作

```cpp
bool setEmpty();
bool setRect(const SkIRect&);
```

设置裁剪区域为空或指定矩形。

### 裁剪操作

```cpp
bool op(const SkIRect&, SkClipOp);
bool op(const SkRegion&, SkClipOp);
bool op(const SkRect&, const SkMatrix& matrix, SkClipOp, bool doAA);
bool op(const SkRRect&, const SkMatrix& matrix, SkClipOp, bool doAA);
bool op(const SkPath&, const SkMatrix& matrix, SkClipOp, bool doAA);
bool op(sk_sp<SkShader>);
```

执行各种裁剪操作，支持矩形、区域、圆角矩形、路径和着色器裁剪。返回 `true` 表示裁剪区域非空。

### 变换操作

```cpp
void translate(int dx, int dy, SkRasterClip* dst) const;
```

将裁剪区域平移指定偏移量，结果存储到 `dst`。

### 快速测试

```cpp
bool quickContains(const SkIRect& rect) const;
bool quickReject(const SkIRect& rect) const;
```

快速判断矩形是否完全被包含或完全不相交。

### 着色器裁剪

```cpp
sk_sp<SkShader> clipShader() const;
```

获取当前的着色器裁剪对象。

## 内部实现细节

### 自动模式切换

`SkRasterClip` 会根据需要自动在 BW 和 AA 模式之间切换：

1. **BW 转 AA**：当调用需要抗锯齿的操作时，通过 `convertToAA()` 方法将 `fBW` 转换为 `fAA`
2. **AA 优化为 BW**：在 `updateCacheAndReturnNonEmpty()` 中检测到 AA 裁剪实际上是硬边矩形时，自动降级为 BW 模式以提高性能

### 近似整数优化

`nearly_integral()` 函数检查浮点坐标是否接近整数（误差小于 1/8 像素）。在矩形裁剪操作中，如果所有坐标都近似整数，则即使请求了抗锯齿也会使用 BW 模式，避免不必要的开销。

### 路径裁剪优化

对于常见的"矩形裁剪区域与路径相交"场景（`isRect() && op == kIntersect`），代码采用特殊优化：直接将路径转换为区域/AA 掩码，而不是计算实际的交集。根据注释，这比真实交集计算更快（参见 skbug.com/40043482）。

### 缓存管理

`fIsEmpty` 和 `fIsRect` 作为缓存标志，避免重复计算：
- 在每次修改操作后通过 `updateCacheAndReturnNonEmpty()` 更新
- 使用 `SkASSERT` 在调试模式下验证缓存的一致性

### 着色器裁剪混合

着色器裁剪通过 `op(sk_sp<SkShader>)` 添加：
- 如果尚无着色器，直接设置
- 如果已有着色器，使用 `SkBlendMode::kSrcIn` 混合模式组合

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `SkRegion` | 位图裁剪区域表示 |
| `SkAAClip` | 抗锯齿裁剪区域表示 |
| `SkRect` / `SkIRect` | 矩形数据结构 |
| `SkPath` | 路径数据结构 |
| `SkRRect` | 圆角矩形数据结构 |
| `SkMatrix` | 变换矩阵 |
| `SkShader` | 着色器接口 |
| `SkBlitter` | 像素填充器接口 |
| `SkClipOp` | 裁剪操作枚举 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkCanvas` | 使用 `SkRasterClip` 实现裁剪功能 |
| `SkDevice` | 设备层使用裁剪信息 |
| `SkDraw` | 绘制操作应用裁剪 |
| `SkScan` | 扫描转换时使用裁剪 |
| `SkRasterClipStack` | 管理裁剪栈 |

## 设计模式与设计决策

### 适配器模式

`SkRasterClip` 作为适配器统一了 `SkRegion` 和 `SkAAClip` 两种不同的裁剪表示，为上层提供一致的接口。客户端代码无需关心内部使用哪种表示。

### 策略模式

根据是否需要抗锯齿，`SkRasterClip` 动态选择使用 BW 或 AA 策略。这种运行时策略选择提供了性能和质量的平衡。

### RAII 模式

`SkAutoRasterClipValidate` 类使用 RAII 模式在作用域进入和退出时自动验证对象状态，确保调试时的正确性。

### 惰性转换

只在真正需要时才从 BW 转换为 AA（通过 `convertToAA()`），避免不必要的内存分配和计算开销。

### 写时复制（COW）思想

虽然不是严格的 COW，但代码在检测到 AA 裁剪实际是简单矩形时会"降级"回 BW 模式，体现了选择最优表示的思想。

## 性能考量

### 内存优化

- **互斥存储**：`fBW` 和 `fAA` 在任何时刻只有一个有效，减少内存占用
- **缓存标志**：`fIsEmpty` 和 `fIsRect` 避免重复计算
- **延迟分配**：只在需要时才分配 AA 裁剪结构

### 计算优化

- **快速路径**：`quickContains()` 和 `quickReject()` 提供 O(1) 的快速判断
- **近似整数检测**：避免对实际是整数坐标的情况使用昂贵的抗锯齿
- **矩形特殊处理**：对常见的矩形裁剪场景使用优化路径

### 模式自动降级

在 `updateCacheAndReturnNonEmpty()` 中，如果检测到 AA 裁剪实际是硬边矩形，会自动转换为 BW 模式。这个优化对于许多实际场景非常有效。

### 跳过不必要的排序

注释提到"在 Y 方向跳过排序调用在录制时带来 17% 的提升，对回放速度影响可忽略不计"，体现了针对实际使用模式的优化。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/core/SkRect.h` | 矩形定义 |
| `include/core/SkRegion.h` | 位图区域 |
| `include/core/SkShader.h` | 着色器接口 |
| `src/core/SkAAClip.h` | 抗锯齿裁剪 |
| `include/core/SkClipOp.h` | 裁剪操作枚举 |
| `include/core/SkMatrix.h` | 变换矩阵 |
| `include/core/SkPath.h` | 路径定义 |
| `src/core/SkRegionPriv.h` | Region 私有接口 |
| `src/core/SkRasterClipStack.h` | 裁剪栈管理 |
| `include/core/SkBlendMode.h` | 混合模式 |
