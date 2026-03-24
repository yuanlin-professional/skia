# DrawableOp

> 源文件
> - src/gpu/ganesh/ops/DrawableOp.h
> - src/gpu/ganesh/ops/DrawableOp.cpp

## 概述

`DrawableOp` 是 Ganesh GPU 后端中用于执行 `SkDrawable` 对象的特殊操作。它允许将自定义的 GPU 绘制命令（通过 `SkDrawable::GpuDrawHandler` 接口）集成到 Ganesh 渲染管线中。这个操作不涉及标准的几何绘制，而是将控制权委托给用户提供的绘制处理器，使得应用可以直接发出原始 GPU 命令或与其他图形 API 互操作。

`DrawableOp` 是最简单的操作类型之一，它不执行准备步骤，不能与其他操作合并，只在执行阶段将 `GpuDrawHandler` 传递给渲染通道。

## 架构位置

`DrawableOp` 位于 Ganesh 渲染管线的操作层：

- **上层**：由 `SurfaceDrawContext` 或 `GrOpsTask` 创建和管理
- **同层**：继承自 `GrOp`，与其他绘制操作并列
- **下层**：通过 `GrOpsRenderPass` 执行 `GpuDrawHandler`

在绘制流水线中，该操作是外部 GPU 命令和 Ganesh 内部管线之间的桥梁。

## 主要类与结构体

### 类层次结构

```
GrOp
    └── DrawableOp (final)
```

### DrawableOp 关键成员

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDrawable` | `unique_ptr<SkDrawable::GpuDrawHandler>` | GPU 绘制处理器 |

该类只有一个成员变量，极其简洁。

### 相关接口

**SkDrawable::GpuDrawHandler**
外部定义的接口，用户实现自定义 GPU 绘制逻辑。具体接口定义在 `include/core/SkDrawable.h` 中。

## 公共 API 函数

### 工厂方法

```cpp
static GrOp::Owner Make(GrRecordingContext* context,
                        std::unique_ptr<SkDrawable::GpuDrawHandler> drawable,
                        const SkRect& bounds)
```
创建 `DrawableOp` 实例。

**参数**：
- `context`：录制上下文
- `drawable`：GPU 绘制处理器，所有权转移给操作
- `bounds`：绘制的边界矩形（用于裁剪和排序）

**返回**：操作的所有权指针。

### 操作接口

```cpp
const char* name() const override
```
返回操作名称 "Drawable"，用于调试和日志。

## 内部实现细节

### 构造函数

```cpp
DrawableOp::DrawableOp(std::unique_ptr<SkDrawable::GpuDrawHandler> drawable,
                       const SkRect& bounds)
        : GrOp(ClassID())
        , fDrawable(std::move(drawable)) {
    this->setBounds(bounds, HasAABloat::kNo, IsHairline::kNo);
}
```

初始化步骤：
1. 调用 `GrOp` 基类构造函数，传递类 ID
2. 移动 `drawable` 所有权到成员变量
3. 设置边界，不包含抗锯齿扩展和细线标志

### 生命周期钩子

**预准备（Pre-Prepare）**：
```cpp
void onPrePrepare(...) override {}
```
空实现，无需预准备步骤。

**准备（Prepare）**：
```cpp
void onPrepare(GrOpFlushState*) override {}
```
空实现，无需准备步骤。

**执行（Execute）**：
```cpp
void DrawableOp::onExecute(GrOpFlushState* state, const SkRect& chainBounds) {
    SkASSERT(state->opsRenderPass());
    state->opsRenderPass()->executeDrawable(std::move(fDrawable));
}
```

执行逻辑：
1. 断言渲染通道存在
2. 将 `fDrawable` 的所有权移动给渲染通道
3. 渲染通道负责调用 `GpuDrawHandler` 的实际绘制方法

### 合并策略

```cpp
CombineResult onCombineIfPossible(GrOp* that, SkArenaAlloc*, const GrCaps& caps) override {
    return CombineResult::kCannotCombine;
}
```

`DrawableOp` 永远不能与其他操作合并，原因：
- 每个 `Drawable` 代表独立的自定义绘制逻辑
- 无法预测或分析 `GpuDrawHandler` 的行为
- 合并可能破坏用户的绘制顺序或语义

### 工厂方法实现

```cpp
GrOp::Owner DrawableOp::Make(GrRecordingContext* context,
                             std::unique_ptr<SkDrawable::GpuDrawHandler> drawable,
                             const SkRect& bounds) {
    return GrOp::Make<DrawableOp>(context, std::move(drawable), bounds);
}
```

使用 `GrOp::Make` 模板方法创建操作，自动处理内存分配。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrOp` | 基类，提供操作框架 |
| `SkDrawable::GpuDrawHandler` | 外部绘制处理器接口 |
| `GrOpFlushState` | 刷新状态 |
| `GrOpsRenderPass` | 渲染通道，执行实际绘制 |
| `SkRect` | 边界矩形 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `SurfaceDrawContext` | 调用 `DrawableOp::Make` 创建操作 |
| `SkCanvas` | 通过 `drawDrawable` 间接创建 `DrawableOp` |
| `GrOpsTask` | 管理和调度 `DrawableOp` |

## 设计模式与设计决策

### 桥接模式

`DrawableOp` 充当桥接角色：
- **Ganesh 侧**：`GrOp` 接口和管线
- **用户侧**：`SkDrawable::GpuDrawHandler` 自定义实现

这种设计允许外部代码无缝集成到 Ganesh 渲染流程中。

### 所有权转移

使用 `std::unique_ptr` 和移动语义管理 `GpuDrawHandler` 的生命周期：
```cpp
state->opsRenderPass()->executeDrawable(std::move(fDrawable));
```

好处：
- 清晰的所有权语义
- 避免拷贝开销
- 自动管理资源释放

### 最小化设计

`DrawableOp` 是最简单的操作实现：
- 无准备步骤
- 无合并逻辑
- 无状态管理
- 仅执行委托

这种设计反映了其作为"黑盒"绘制的本质。

### 边界语义

虽然 `GpuDrawHandler` 的行为不透明，但仍需要提供边界：
- 用于裁剪决策：确定哪些裁剪元素影响该绘制
- 用于排序：确定与其他操作的相对顺序
- 用于优化：跳过完全在视口外的绘制

边界必须由调用者正确提供，因为 Ganesh 无法分析 `GpuDrawHandler` 的实际绘制范围。

### 不可合并性

设计决策：`DrawableOp` 永不合并，原因：

1. **语义不透明**：无法分析 `GpuDrawHandler` 的行为
2. **顺序敏感**：自定义绘制可能依赖严格的执行顺序
3. **状态副作用**：可能修改 GPU 状态，影响后续绘制
4. **简化实现**：避免复杂的合并逻辑

### 延迟执行

`GpuDrawHandler` 在 `onExecute` 阶段才被调用：
- 支持录制/回放模型
- 允许操作重排序和优化
- 确保在正确的渲染通道中执行

### 无预准备支持

`onPrePrepare` 为空，不支持延迟显示列表（DDL）预准备：
- `GpuDrawHandler` 通常需要实际的 GPU 上下文
- 预准备阶段没有可用的 GPU 资源
- 自定义绘制的复杂性使预准备不实际

## 性能考量

### 零准备开销

`DrawableOp` 不执行任何准备步骤：
- 无缓冲区分配
- 无数据传输
- 无着色器编译
- 仅在执行时调用 `GpuDrawHandler`

适合已预准备的外部绘制逻辑。

### 不可合并的代价

由于永不合并：
- 每个 `DrawableOp` 独立处理
- 可能增加渲染通道切换
- 无法利用批处理优化

权衡：灵活性 vs 性能。

### 移动语义优化

使用移动语义转移 `unique_ptr`：
```cpp
state->opsRenderPass()->executeDrawable(std::move(fDrawable));
```

避免：
- 引用计数开销（如果使用 `shared_ptr`）
- 不必要的拷贝
- 额外的内存分配

### 边界剔除

准确的边界允许 Ganesh 剔除不可见的 `DrawableOp`：
- 减少不必要的 `GpuDrawHandler` 调用
- 降低 GPU 负载

但边界过于保守可能导致不必要的执行。

### 状态管理成本

`GpuDrawHandler` 可能修改 GPU 状态：
- Ganesh 可能需要在 `DrawableOp` 后恢复状态
- 增加状态切换开销

用户应尽量保持状态隔离。

### 适用场景

`DrawableOp` 适合以下场景：

**适合**：
- 集成第三方渲染库（如 WebGL、Metal 自定义命令）
- 绕过 Ganesh 进行底层优化
- 实现 Skia 不支持的特殊效果
- 与其他图形管线互操作

**不适合**：
- 常规几何绘制（使用 `GrMeshDrawOp` 子类更高效）
- 需要合并优化的批量绘制
- 需要 DDL 预准备的场景

### 调试与跟踪

`DrawableOp` 的名称 "Drawable" 简单明了：
```cpp
const char* name() const override { return "Drawable"; }
```

有助于：
- 性能分析工具识别自定义绘制
- 调试日志追踪操作流程
- 区分标准和自定义绘制

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrOp.h` | 继承 | 操作基类 |
| `include/core/SkDrawable.h` | 依赖 | `GpuDrawHandler` 接口定义 |
| `src/gpu/ganesh/GrOpFlushState.h` | 使用 | 刷新状态 |
| `src/gpu/ganesh/GrOpsRenderPass.h` | 使用 | 渲染通道执行 |
| `src/gpu/ganesh/GrOpsTask.h` | 被使用 | 任务管理 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 被使用 | 上下文创建操作 |
