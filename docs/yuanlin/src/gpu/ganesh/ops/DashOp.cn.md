# DashOp / DashLinePathRenderer

> 源文件
> - src/gpu/ganesh/ops/DashOp.h
> - src/gpu/ganesh/ops/DashLinePathRenderer.h

## 概述

`DashOp` 和 `DashLinePathRenderer` 是 Skia Ganesh GPU 后端用于渲染虚线的模块。`DashOp` 提供核心的虚线绘制操作，支持抗锯齿和多种虚线样式。`DashLinePathRenderer` 作为路径渲染器包装器，将虚线路径转换为 `DashOp` 操作。

虚线渲染是 2D 图形中的常见需求，该模块通过 GPU 着色器实现高效的虚线效果，支持 dash-dot 模式、dash offset、线段端点样式等特性。

## 架构位置

```
Skia GPU 渲染架构:
├── PathRenderer 系统
│   ├── DashLinePathRenderer ← 路径渲染器入口
│   ├── AAHairLinePathRenderer
│   └── DefaultPathRenderer
└── GrOp 操作层
    └── DashOp ← 核心虚线操作
        ├── MakeDashLineOp (工厂方法)
        └── CanDrawDashLine (能力查询)
```

## 主要类与结构体

### DashOp 命名空间

提供虚线操作的工厂方法和辅助函数。

### AAMode 枚举

| 枚举值 | 说明 |
|-------|------|
| `kNone` | 无抗锯齿 |
| `kCoverage` | 覆盖率抗锯齿 |
| `kCoverageWithMSAA` | 覆盖率抗锯齿配合 MSAA |

### DashLinePathRenderer 类

继承自 `PathRenderer`。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 无公共成员变量 | - | 无状态渲染器 |

## 公共 API 函数

### DashOp 命名空间函数

```cpp
GrOp::Owner MakeDashLineOp(GrRecordingContext*, GrPaint&&,
                           const SkMatrix& viewMatrix, const SkPoint pts[2],
                           AAMode, const GrStyle& style,
                           const GrUserStencilSettings*)
```
创建虚线绘制操作。参数：
- `pts[2]`：线段的起点和终点
- `AAMode`：抗锯齿模式
- `style`：包含 dash 信息的样式对象

```cpp
bool CanDrawDashLine(const SkPoint pts[2], const GrStyle& style,
                    const SkMatrix& viewMatrix)
```
检查是否可以绘制指定的虚线。返回 `true` 表示支持。

### DashLinePathRenderer 接口

```cpp
const char* name() const override
```
返回渲染器名称 "DashLine"。

```cpp
CanDrawPath onCanDrawPath(const CanDrawPathArgs&) const override
```
判断是否可以渲染给定的虚线路径。检查路径是否为单线段且具有 dash effect。

```cpp
StencilSupport onGetStencilSupport(const GrStyledShape&) const override
```
返回 `kNoSupport_StencilSupport`，虚线渲染不支持模板缓冲。

```cpp
bool onDrawPath(const DrawPathArgs&) override
```
执行虚线路径渲染，调用 `DashOp::MakeDashLineOp` 创建操作。

## 内部实现细节

### 虚线模式编码

`GrStyle` 对象包含虚线模式信息：
- **Dash 数组**：交替的实线和空隙长度
- **Dash Count**：数组中元素数量
- **Dash Offset**：虚线模式的起始偏移

### GPU 着色器实现

虚线渲染通过几何着色器或片段着色器实现：
1. 生成覆盖整个线段的几何体
2. 在片段着色器中计算沿线段的距离
3. 根据 dash 模式决定片段可见性
4. 应用抗锯齿覆盖率

### 抗锯齿策略

三种抗锯齿模式：
- **kNone**：无抗锯齿，硬边缘
- **kCoverage**：覆盖率抗锯齿，边缘渐变
- **kCoverageWithMSAA**：覆盖率 + MSAA 组合

### 端点处理

虚线段的端点根据样式渲染：
- **Butt Cap**：方形端点
- **Round Cap**：圆形端点
- **Square Cap**：延长的方形端点

### 坐标变换

支持任意仿射变换（缩放、旋转、倾斜）：
- 透视变换可能不支持（取决于实现）
- 变换应用于线段坐标和 dash 长度

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrOp` | 继承 | 操作基类 |
| `PathRenderer` | 继承 | 路径渲染器基类 |
| `GrStyle` | 依赖 | 样式信息，包含 dash 模式 |
| `GrPaint` | 依赖 | 绘制颜色和效果 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `SurfaceDrawContext` | 使用 | 通过路径渲染器使用虚线渲染 |
| `PathRendererChain` | 注册 | 作为可选路径渲染器 |

## 设计模式与设计决策

### 1. 分离接口设计

`DashOp` 和 `DashLinePathRenderer` 分离：
- **DashOp**：底层操作，可独立使用
- **DashLinePathRenderer**：路径渲染器接口适配
- **灵活性**：支持多种使用场景

### 2. 能力查询函数

提供 `CanDrawDashLine` 查询函数：
- 在创建操作前检查可行性
- 避免不必要的操作创建和失败

### 3. 模板不支持决策

虚线渲染器不支持模板：
- **原因**：虚线逻辑在片段着色器中
- **简化**：避免复杂的模板交互

### 4. 抗锯齿模式分层

提供三种抗锯齿模式：
- 适应不同硬件能力和质量需求
- 灵活的性能-质量权衡

## 性能考量

### 1. GPU 加速

虚线模式计算在 GPU 着色器中：
- 避免 CPU 端的复杂几何生成
- 充分利用并行计算能力

### 2. 几何体简化

生成覆盖线段的简单矩形：
- 减少顶点数量
- 片段着色器负责精细控制

### 3. 批处理潜力

相似的虚线段可以批处理：
- 共享几何处理器和管线
- 减少状态切换

### 4. 抗锯齿开销

根据场景选择合适的抗锯齿模式：
- kNone：最快，适合精确像素对齐
- kCoverage：中等，高质量边缘
- kCoverageWithMSAA：最慢，最高质量

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrOp.h` | 基类 | 操作基类 |
| `src/gpu/ganesh/PathRenderer.h` | 基类 | 路径渲染器基类 |
| `src/gpu/ganesh/GrStyle.h` | 依赖 | 样式信息，包含 dash 模式 |
| `src/gpu/ganesh/GrPaint.h` | 依赖 | 绘制参数 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 使用者 | 表面绘制上下文 |
