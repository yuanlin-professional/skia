# GrOvalOpFactory

> 源文件
> - src/gpu/ganesh/ops/GrOvalOpFactory.h
> - src/gpu/ganesh/ops/GrOvalOpFactory.cpp

## 概述

`GrOvalOpFactory` 是 Ganesh GPU 后端中用于创建椭圆、圆形、圆角矩形和圆弧绘制操作的工厂类。它提供了一组静态方法来生成填充和描边（stroke）这些几何图元的专用操作。该工厂使用高度优化的自定义几何处理器，在片段着色器中通过解析几何方程计算抗锯齿覆盖率，避免了传统路径渲染的开销。

该实现在 `SK_ENABLE_OPTIMIZE_SIZE` 宏未定义时编译，提供高性能但较大代码体积的圆形几何渲染。文件包含多个复杂的几何处理器实现，总计超过 3600 行代码。

## 架构位置

`GrOvalOpFactory` 位于 Ganesh 图形管线的形状绘制层：

- **上层**：由 `SurfaceDrawContext` 调用，响应高层绘制 API（`drawCircle`, `drawOval`, `drawArc` 等）
- **同层**：与其他形状操作工厂（如 `FillRectOp`, `FillRRectOp`）并列
- **下层**：创建 `GrMeshDrawOp` 子类，使用专用几何处理器

在绘制流水线中，该工厂是圆形/椭圆形状描述和底层 GPU 绘制操作之间的转换层。

## 主要类与结构体

### GrOvalOpFactory 工厂类

`GrOvalOpFactory` 不是可实例化的类，而是一组静态工厂方法的集合。

### 工厂方法

| 方法 | 用途 |
|------|------|
| `MakeCircleOp()` | 创建圆形填充/描边操作 |
| `MakeOvalOp()` | 创建椭圆填充/描边操作 |
| `MakeCircularRRectOp()` | 创建圆形圆角矩形操作 |
| `MakeRRectOp()` | 创建一般圆角矩形操作 |
| `MakeArcOp()` | 创建圆弧操作 |

### 几何处理器

文件内部实现了多个专用几何处理器（在匿名命名空间中）：

| 处理器 | 说明 |
|--------|------|
| `CircleGeometryProcessor` | 圆形和圆弧处理器，支持裁剪平面和圆角端点 |
| `ButtCapDashedCircleGeometryProcessor` | 平头虚线圆形处理器 |
| `EllipseGeometryProcessor` | 椭圆处理器 |
| `DIEllipseGeometryProcessor` | 双内椭圆处理器（描边椭圆优化） |
| `CircularRRectOp` | 圆形圆角矩形操作实现 |
| `EllipticalRRectOp` | 椭圆形圆角矩形操作实现 |

### 顶点属性（CircleGeometryProcessor 示例）

| 属性 | 类型 | 说明 |
|------|------|------|
| `inPosition` | `float2` | 设备空间位置 |
| `inColor` | `ubyte4/float4` | 颜色（根据 wideColor 标志） |
| `inCircleEdge` | `float4` | (p.xy, outerRad, innerRad) - 标准化空间位置和半径 |
| `inClipPlane` | `float3`（可选） | 裁剪平面参数 |
| `inIsectPlane` | `float3`（可选） | 相交裁剪平面 |
| `inUnionPlane` | `float3`（可选） | 联合裁剪平面 |
| `inRoundCapCenters` | `float4`（可选） | 圆角端点中心 |

## 公共 API 函数

### 圆形操作

```cpp
static GrOp::Owner MakeCircleOp(GrRecordingContext* context,
                                GrPaint&& paint,
                                const SkMatrix& viewMatrix,
                                const SkRect& oval,
                                const GrStyle& style,
                                const GrShaderCaps* shaderCaps)
```

创建圆形填充或描边操作。

**前提条件**：
- `oval` 必须是正方形
- 变换后仍保持圆形（`circle_stays_circle(viewMatrix)` 即 `isSimilarity()`）

**参数**：
- `context`：录制上下文
- `paint`：绘制属性
- `viewMatrix`：视图变换矩阵
- `oval`：包围圆形的矩形
- `style`：样式（填充或描边参数）
- `shaderCaps`：着色器能力

### 椭圆操作

```cpp
static GrOp::Owner MakeOvalOp(GrRecordingContext* context,
                              GrPaint&& paint,
                              const SkMatrix& viewMatrix,
                              const SkRect& oval,
                              const GrStyle& style,
                              const GrShaderCaps* shaderCaps)
```

创建椭圆填充或描边操作。

支持任意椭圆形状，无需保持圆形。

### 圆形圆角矩形操作

```cpp
static GrOp::Owner MakeCircularRRectOp(GrRecordingContext* context,
                                       GrPaint&& paint,
                                       const SkMatrix& viewMatrix,
                                       const SkRRect& rrect,
                                       const SkStrokeRec& stroke,
                                       const GrShaderCaps* shaderCaps)
```

创建圆形圆角矩形操作（所有角的半径相同且为圆形）。

**优化路径**：针对简单圆角矩形的特化实现。

### 一般圆角矩形操作

```cpp
static GrOp::Owner MakeRRectOp(GrRecordingContext* context,
                               GrPaint&& paint,
                               const SkMatrix& viewMatrix,
                               const SkRRect& rrect,
                               const SkStrokeRec& stroke,
                               const GrShaderCaps* shaderCaps)
```

创建一般圆角矩形操作（支持椭圆角和不同角半径）。

### 圆弧操作

```cpp
static GrOp::Owner MakeArcOp(GrRecordingContext* context,
                             GrPaint&& paint,
                             const SkMatrix& viewMatrix,
                             const SkRect& oval,
                             SkScalar startAngle,
                             SkScalar sweepAngle,
                             bool useCenter,
                             const GrStyle& style,
                             const GrShaderCaps* shaderCaps)
```

创建圆弧操作。

**参数**：
- `startAngle`：起始角度（弧度）
- `sweepAngle`：扫过角度（弧度）
- `useCenter`：是否连接到中心（扇形 vs 弧段）
- `style`：样式（填充或描边）

## 内部实现细节

### 圆形保持性检查

```cpp
static inline bool circle_stays_circle(const SkMatrix& m) {
    return m.isSimilarity();
}
```

检查矩阵是否为相似变换（平移+旋转+均匀缩放），这种变换保持圆形不变。

### 圆形覆盖率计算

在 `CircleGeometryProcessor` 片段着色器中：

```glsl
float d = length(circleEdge.xy);
half distanceToOuterEdge = half(circleEdge.z * (1.0 - d));
half edgeAlpha = saturate(distanceToOuterEdge);
```

**原理**：
- `circleEdge.xy`：标准化空间中的位置（外圆半径为 1）
- `d`：距离圆心的距离
- `circleEdge.z`：设备空间外半径（用于反标准化）
- `distanceToOuterEdge`：到外边缘的距离，用于抗锯齿

### 描边圆形

```glsl
if (stroke) {
    half distanceToInnerEdge = half(circleEdge.z * (d - circleEdge.w));
    half innerAlpha = saturate(distanceToInnerEdge);
    edgeAlpha *= innerAlpha;
}
```

**原理**：
- `circleEdge.w`：标准化空间内半径
- 同时检查外边缘和内边缘
- 覆盖率为两者的乘积

### 裁剪平面

支持最多 3 个裁剪平面用于圆弧渲染：

```glsl
half clip = half(saturate(circleEdge.z * dot(circleEdge.xy, clipPlane.xy) + clipPlane.z));
if (isectPlane) {
    clip *= half(saturate(circleEdge.z * dot(circleEdge.xy, isectPlane.xy) + isectPlane.z));
}
if (unionPlane) {
    clip = saturate(clip + half(saturate(circleEdge.z * dot(circleEdge.xy, unionPlane.xy) + unionPlane.z)));
}
edgeAlpha *= clip;
```

**用途**：
- **初始平面**：定义弧的起始边
- **相交平面**：定义弧的结束边（与初始平面相交）
- **联合平面**：用于特殊弧情况（与前两个平面联合）

### 圆角端点

对于描边圆弧，支持圆角端点：

```glsl
half dcap1 = half(circleEdge.z * (capRadius - length(circleEdge.xy - roundCapCenters.xy)));
half dcap2 = half(circleEdge.z * (capRadius - length(circleEdge.xy - roundCapCenters.zw)));
half capAlpha = (1 - clip) * (max(dcap1, 0) + max(dcap2, 0));
edgeAlpha = min(edgeAlpha + capAlpha, 1.0);
```

**原理**：
- 将端点建模为圆形
- 在裁剪平面裁剪区域外增加覆盖率
- 避免重复计数（`1 - clip` 项）

### 虚线圆形

`ButtCapDashedCircleGeometryProcessor` 实现虚线圆形：

**顶点着色器**：
- 计算边界虚线间隔（跨越 2π 边界）
- 预计算包裹虚线参数

**片段着色器**：
- 计算角度位置在虚线模式中的位置
- 检查当前、前一个和后一个虚线段的覆盖率
- 处理 2π 边界的特殊情况

### 椭圆处理

`EllipseGeometryProcessor` 使用椭圆方程：

```glsl
vec2 scaledOffset = offset * invRadii;
float test = dot(scaledOffset, scaledOffset) - 1.0;
vec2 grad = 2.0 * scaledOffset * invRadii;
float gradDot = dot(grad, grad);
gradDot = max(gradDot, 1.0e-4);
float invLength = inversesqrt(gradDot);
float coverage = test * invLength;
```

**原理**：
- 隐式椭圆方程：`(x/a)² + (y/b)² - 1 = 0`
- 计算梯度用于抗锯齿
- 使用符号距离场确定覆盖率

### 双内椭圆（DIEllipse）

`DIEllipseGeometryProcessor` 用于描边椭圆的优化：

**策略**：
- 使用两个椭圆（外椭圆和内椭圆）
- 避免单椭圆方法中的数值问题
- 分别计算到两个边缘的距离

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrMeshDrawOp` | 操作基类 |
| `GrGeometryProcessor` | 几何处理器基类 |
| `GrSimpleMeshDrawOpHelper` | 操作辅助类 |
| `GrPaint` | 绘制属性 |
| `GrStyle` | 样式（填充/描边） |
| `SkMatrix` | 变换矩阵 |
| `SkRRect` | 圆角矩形 |
| `SkStrokeRec` | 描边记录 |
| `GrShaderCaps` | 着色器能力 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SurfaceDrawContext` | 调用工厂方法创建操作 |
| `SkCanvas` | 通过 `drawCircle`, `drawOval`, `drawArc` 间接使用 |
| 路径渲染器 | 将圆形/椭圆路径委托给该工厂 |

## 设计模式与设计决策

### 工厂模式

使用静态工厂方法而非直接构造：
- 隐藏实现细节
- 根据参数选择最优实现
- 返回空指针表示无法处理（回退到路径渲染）

### 解析几何方法

使用解析几何方程而非镶嵌：
- **圆形**：在片段着色器中计算距离 `d = length(p)`
- **椭圆**：使用椭圆方程 `(x/a)² + (y/b)² = 1`
- **抗锯齿**：基于距离函数的梯度

**优势**：
- 精确的抗锯齿
- 无需细分几何体
- 适应任意缩放级别

### 裁剪平面技术

使用裁剪平面实现圆弧：
- 避免复杂的三角剖分
- 在片段着色器中高效计算
- 支持任意角度范围

### 圆形 vs 椭圆分离

区分圆形和椭圆操作：
- **圆形**：简化的着色器，单个半径参数
- **椭圆**：完整椭圆方程，两个半径参数

权衡：代码复杂度 vs 性能。

### 描边优化

不同的描边策略：
- **圆形描边**：外半径和内半径
- **椭圆描边（DIEllipse）**：双椭圆方法避免数值问题
- **虚线描边**：专用处理器

### 条件编译

通过 `SK_ENABLE_OPTIMIZE_SIZE` 控制编译：
```cpp
#if !defined(SK_ENABLE_OPTIMIZE_SIZE)
// 整个实现
#endif
```

**原因**：该实现高性能但代码体积大（3600+ 行），尺寸优化构建中禁用，回退到通用路径渲染。

### 圆角端点实现

描边弧线支持圆角端点：
- 建模为额外的圆形
- 在裁剪平面外添加覆盖率
- 平滑的视觉效果

### 虚线边界处理

虚线圆形在 2π 边界处特殊处理：
- 预计算边界虚线间隔
- 在顶点着色器中处理，减少片段着色器复杂度
- 正确处理非整数周期

## 性能考量

### 解析几何的优势

相比镶嵌路径：
- **零几何开销**：只需 4 个顶点（矩形）
- **精确**：任意缩放下都完美
- **内存高效**：无需存储大量三角形

### 片段着色器成本

使用片段着色器计算覆盖率：
- **优势**：几何简单，适合 GPU 并行
- **劣势**：每像素都执行着色器
- **适用**：中小尺寸圆形/椭圆（大圆形可能镶嵌更快）

### 裁剪平面开销

圆弧使用裁剪平面：
- 增加片段着色器指令
- 但避免复杂几何生成
- 整体上更高效

### 批处理机会

圆形/椭圆操作可以合并：
- 相同着色器变体
- 兼容的绘制状态
- 减少绘制调用

### 虚线性能

虚线圆形着色器复杂：
- 大量三角函数（atan, sin等）
- 边界条件处理
- 适合静态虚线图案

### 双内椭圆优化

`DIEllipseGeometryProcessor` 避免数值问题：
- 薄描边椭圆中单椭圆方法不稳定
- 双椭圆方法数值更稳定
- 轻微增加着色器复杂度，但避免伪影

### 代码体积权衡

整个文件超过 3600 行：
- 多个专用几何处理器
- 复杂的着色器代码
- 可通过 `SK_ENABLE_OPTIMIZE_SIZE` 禁用

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrMeshDrawOp.h` | 继承 | 网格绘制操作基类 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 使用 | 几何处理器基类 |
| `src/gpu/ganesh/ops/GrSimpleMeshDrawOpHelper.h` | 使用 | 操作辅助类 |
| `src/gpu/ganesh/GrStyle.h` | 使用 | 样式定义 |
| `include/core/SkRRect.h` | 使用 | 圆角矩形 |
| `include/core/SkStrokeRec.h` | 使用 | 描边记录 |
| `src/gpu/ganesh/ops/FillRRectOp.h` | 相关 | 圆角矩形填充（不同实现） |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 被使用 | 绘制上下文调用工厂 |
| `src/gpu/ganesh/GrPathRenderer.h` | 协作 | 路径渲染器可能委托给该工厂 |

## 总结

`GrOvalOpFactory` 是 Skia GPU 渲染中圆形几何的专家系统：
- **高性能**：解析几何方法，精确抗锯齿
- **完整功能**：填充、描边、虚线、圆弧、圆角端点
- **复杂实现**：3600+ 行，多个专用处理器
- **可选编译**：尺寸优化时禁用

它体现了性能优化的极致：为常见图元（圆形/椭圆）编写专用代码，以换取最佳渲染质量和性能。
