# DashLinePathRenderer

> 源文件
> - src/gpu/ganesh/ops/DashLinePathRenderer.h

## 概述

`DashLinePathRenderer` 是 Skia Ganesh GPU 后端的虚线路径渲染器，专门用于渲染具有虚线样式的直线路径。该渲染器作为 `PathRenderer` 系统的一部分，将虚线路径转换为 `DashOp` 操作进行 GPU 加速渲染。

该渲染器简化了虚线渲染的路径选择逻辑，将实际的渲染工作委托给专门的 `DashOp`，实现了关注点分离和代码复用。

## 架构位置

```
Skia GPU 渲染架构:
├── PathRenderer 系统
│   ├── AAHairLinePathRenderer
│   ├── DashLinePathRenderer ← 本类
│   ├── AtlasPathRenderer
│   └── DefaultPathRenderer
└── GrOp 操作层
    └── DashOp (实际虚线渲染)
```

## 主要类与结构体

### DashLinePathRenderer 类

继承自 `PathRenderer`，提供虚线路径渲染能力。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 无公共成员变量 | - | 无状态渲染器，所有逻辑委托给 DashOp |

## 公共 API 函数

### PathRenderer 接口

```cpp
const char* name() const override
```
返回渲染器名称 "DashLine"，用于调试和日志。

```cpp
CanDrawPath onCanDrawPath(const CanDrawPathArgs&) const override
```
判断是否可以渲染给定的虚线路径。检查条件：
- 路径必须是单个线段
- 必须具有 dash path effect
- 通过 `DashOp::CanDrawDashLine` 验证

返回 `CanDrawPath::kYes` 或 `CanDrawPath::kNo`。

```cpp
StencilSupport onGetStencilSupport(const GrStyledShape&) const override
```
返回 `kNoSupport_StencilSupport`，虚线渲染器不支持模板缓冲区操作。

```cpp
bool onDrawPath(const DrawPathArgs&) override
```
执行虚线路径渲染。实现步骤：
1. 从 `GrStyledShape` 提取路径和样式
2. 验证路径为单线段
3. 调用 `DashOp::MakeDashLineOp` 创建操作
4. 将操作添加到 `SurfaceDrawContext`

## 内部实现细节

### 路径验证

`onCanDrawPath` 验证路径类型：
- 检查路径段掩码，确保只有直线段
- 检查样式是否包含 dash effect
- 调用 `DashOp::CanDrawDashLine` 进行详细验证

### 样式提取

从 `GrStyledShape` 提取虚线参数：
- **Dash 数组**：实线和空隙长度
- **Dash Count**：数组元素数量
- **Dash Offset**：虚线模式起始偏移
- **描边宽度**：线段宽度（通常为 hairline）

### 抗锯齿模式映射

将 `GrAAType` 映射到 `DashOp::AAMode`：
- `GrAAType::kNone` → `DashOp::AAMode::kNone`
- `GrAAType::kCoverage` → `DashOp::AAMode::kCoverage`
- `GrAAType::kMSAA` → `DashOp::AAMode::kCoverageWithMSAA`

### 操作创建

调用 `DashOp::MakeDashLineOp` 创建虚线操作：
```cpp
auto op = DashOp::MakeDashLineOp(
    context, std::move(paint), viewMatrix, pts,
    aaMode, style, stencilSettings);
```

### 无模板支持

`onGetStencilSupport` 返回 `kNoSupport_StencilSupport`：
- **原因**：虚线逻辑在片段着色器中实现
- **影响**：无法与模板操作配合
- **权衡**：简化实现，满足大多数使用场景

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `PathRenderer` | 继承 | 路径渲染器基类 |
| `DashOp` | 强依赖 | 实际的虚线绘制操作 |
| `GrStyledShape` | 依赖 | 封装路径和样式 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `PathRendererChain` | 注册 | 作为可选路径渲染器之一 |
| `SurfaceDrawContext` | 使用 | 通过路径渲染器选择机制使用 |

## 设计模式与设计决策

### 1. 适配器模式

`DashLinePathRenderer` 作为 `PathRenderer` 和 `DashOp` 之间的适配器：
- **接口适配**：将 `PathRenderer` 接口适配到 `DashOp`
- **职责分离**：路径选择逻辑与渲染逻辑分离
- **代码复用**：`DashOp` 可被其他模块直接使用

### 2. 委托模式

所有实际渲染工作委托给 `DashOp`：
- **简化实现**：渲染器本身非常简单
- **关注点分离**：专注于路径选择和参数转换
- **灵活性**：`DashOp` 可独立演化

### 3. 无状态设计

渲染器本身不保存任何状态：
- **简化并发**：多线程安全
- **易于测试**：无需设置状态
- **清晰接口**：所有参数通过方法传递

### 4. 早期拒绝策略

在 `onCanDrawPath` 阶段尽早拒绝不支持的路径：
- **性能优化**：避免不必要的操作创建
- **清晰错误**：明确渲染器的能力边界
- **降级路径**：让其他渲染器处理不支持的路径

## 性能考量

### 1. 快速路径验证

`onCanDrawPath` 快速检查路径类型：
- 检查段掩码（位操作，O(1)）
- 检查 dash effect 存在（O(1)）
- 委托详细检查给 `DashOp`

### 2. 无额外开销

渲染器本身不引入额外开销：
- 无状态管理
- 无复杂计算
- 直接委托给 `DashOp`

### 3. 操作级优化

实际性能由 `DashOp` 决定：
- GPU 着色器实现虚线模式
- 批处理兼容的虚线段
- 硬件加速计算

### 4. 模板不支持的影响

不支持模板限制了某些使用场景：
- 无法与复杂裁剪配合
- 无法参与模板填充算法
- 适合大多数常见虚线绘制

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/PathRenderer.h` | 基类 | 路径渲染器抽象接口 |
| `src/gpu/ganesh/ops/DashOp.h` | 核心依赖 | 虚线绘制操作 |
| `src/gpu/ganesh/geometry/GrStyledShape.h` | 依赖 | 封装路径和样式 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 使用者 | 表面绘制上下文 |
| `src/gpu/ganesh/GrStyle.h` | 依赖 | 样式信息，包含 dash 模式 |
