# GrDrawOp

> 源文件
> - src/gpu/ganesh/ops/GrDrawOp.h

## 概述

`GrDrawOp` 是 Ganesh GPU 后端中所有绘制操作的抽象基类。它继承自 `GrOp`，专门表示那些会向渲染目标绘制内容的操作。该类定义了绘制操作的核心接口，包括 MSAA 使用查询、模板测试支持、裁剪优化和资源终结化。

`GrDrawOp` 是一个非常薄的抽象层，主要作用是区分绘制操作和非绘制操作（如传输操作、清除操作等），并提供裁剪和终结化的标准接口。

## 架构位置

`GrDrawOp` 位于 Ganesh 操作层次结构的中间层：

- **上层**：由 `GrOpsTask` 管理和调度
- **同层**：继承自 `GrOp`，与其他操作类型（如传输操作）并列
- **下层**：被所有具体绘制操作继承，如 `GrMeshDrawOp`、`GrPathOp` 等

在渲染管线中，该类是通用操作接口和具体绘制操作之间的关键分类层。

## 主要类与结构体

### 类层次结构

```
GrOp
    └── GrDrawOp (抽象基类)
        ├── GrMeshDrawOp (网格绘制)
        ├── GrPathOp (路径绘制)
        ├── DrawableOp (自定义绘制)
        └── 其他绘制操作
```

### FixedFunctionFlags 枚举

固定功能标志，用于声明操作使用的固定管线功能：

| 标志 | 值 | 说明 |
|------|---|------|
| `kNone` | 0x0 | 无特殊标志 |
| `kUsesHWAA` | 0x1 | 使用硬件抗锯齿（MSAA） |
| `kUsesStencil` | 0x2 | 读取和/或写入模板缓冲区 |

### ClipResult 枚举

表示 `clipToShape()` 的裁剪结果：

| 枚举值 | 说明 |
|--------|------|
| `kFail` | 未应用裁剪，需要通用裁剪方法 |
| `kClippedGeometrically` | 裁剪已应用到几何体，可禁用剪刀测试 |
| `kClippedInShader` | 裁剪在着色器中应用，仍需剪刀测试减少透明像素 overdraw |
| `kClippedOut` | 操作被完全裁剪掉，可以丢弃 |

## 公共 API 函数

### MSAA 查询

```cpp
virtual bool usesMSAA() const
```
查询操作是否使用 MSAA（多重采样抗锯齿）。

默认实现检查 `fixedFunctionFlags()` 是否包含 `kUsesHWAA` 标志。

### 模板查询

```cpp
virtual bool usesStencil() const
```
查询操作是否使用模板缓冲区。

默认实现检查 `fixedFunctionFlags()` 是否包含 `kUsesStencil` 标志。

在 `finalize()` 之后调用，此时操作应该已知是否需要模板。

### 裁剪优化

```cpp
virtual ClipResult clipToShape(skgpu::ganesh::SurfaceDrawContext* sdc,
                               SkClipOp clipOp,
                               const SkMatrix& clipMatrix,
                               const GrShape& shape,
                               GrAA aa)
```
尝试将裁剪形状直接应用到操作的几何体上。

**调用时机**：在计算 `GrAppliedClip` 期间，`finalize()` 之前，任何合并尝试之前。

**参数**：
- `sdc`：表面绘制上下文
- `clipOp`：裁剪操作（交集/差集等）
- `clipMatrix`：裁剪变换矩阵
- `shape`：裁剪形状
- `aa`：裁剪边缘是否抗锯齿

**返回**：裁剪结果（`ClipResult` 枚举）

**优势**：如果操作知道如何裁剪自己的几何体，通常比通用裁剪方法快得多。

默认实现返回 `kFail`，子类可以重写以实现优化。

### 终结化

```cpp
virtual GrProcessorSet::Analysis finalize(const GrCaps& caps,
                                          const GrAppliedClip* clip,
                                          GrClampType clampType) = 0
```
在计算 `GrAppliedClip` 之后、记录或合并操作之前调用的纯虚函数。

**职责**：
1. 将拥有的代理或资源转换为"待 IO"状态，优化资源分配
2. 报告是否需要目标拷贝或目标纹理给 `GrXferProcessor`
3. 执行处理器分析（颜色、覆盖率等）

**参数**：
- `caps`：GPU 能力
- `clip`：应用的裁剪
- `clampType`：颜色钳制类型

**返回**：`GrProcessorSet::Analysis` 结果，包含颜色和覆盖率分析。

## 内部实现细节

### 构造函数

```cpp
GrDrawOp(uint32_t classID) : INHERITED(classID) {}
```

简单地调用基类 `GrOp` 的构造函数，传递类 ID。

### 固定功能标志（已弃用）

```cpp
virtual FixedFunctionFlags fixedFunctionFlags() const {
    SK_ABORT("fixedFunctionFlags() not implemented.");
}
```

这是一个遗留接口，用于声明 MSAA 和模板使用。

**弃用说明**：新操作应直接重写 `usesMSAA()` 和 `usesStencil()` 方法，而不是使用 `fixedFunctionFlags()`。

默认实现会中止，强制子类实现新接口或旧接口之一。

### 调试验证

```cpp
#ifdef SK_DEBUG
bool fAddDrawOpCalled = false;

void validate() const override {
    SkASSERT(fAddDrawOpCalled);
}
#endif
```

调试模式下，验证操作已通过 `addDrawOp()` 正确添加到任务中。

### 测试工具

```cpp
#if defined(GPU_TEST_UTILS)
virtual int numQuads() const { return -1; }
#endif
```

仅用于测试，允许 `TextureOp` 和 `FillRectOp` 报告包含的四边形数量。

默认返回 -1 表示不适用。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrOp` | 基类 |
| `GrProcessorSet` | 处理器集合和分析 |
| `GrCaps` | GPU 能力查询 |
| `GrAppliedClip` | 应用的裁剪 |
| `GrShape` | 形状表示 |
| `SurfaceDrawContext` | 绘制上下文 |

### 被依赖的模块

`GrDrawOp` 是所有绘制操作的基类：

| 操作类 | 说明 |
|--------|------|
| `GrMeshDrawOp` | 网格绘制操作基类 |
| `GrPathOp` | 路径绘制操作 |
| `DrawableOp` | 自定义绘制 |
| `FillRectOp` | 矩形填充 |
| `FillRRectOp` | 圆角矩形填充 |
| `TextureOp` | 纹理绘制 |
| 等等 | 所有具体绘制操作 |

## 设计模式与设计决策

### 薄抽象层

`GrDrawOp` 是一个非常薄的抽象层：
- 仅定义 3 个核心接口（`finalize`, `clipToShape`, 固定功能标志）
- 大部分功能委托给子类或辅助类
- 主要作用是类型区分（绘制 vs 非绘制操作）

### 裁剪优化钩子

`clipToShape()` 提供了裁剪优化的扩展点：
- **通用路径**：返回 `kFail`，使用标准裁剪机制
- **优化路径**：操作自行裁剪几何体，避免剪刀测试或着色器裁剪开销

例如，`FillRRectOp` 可以将圆角矩形裁剪形状直接与自身圆角矩形相交，生成更小的几何体。

### 终结化时机

`finalize()` 在特定时机调用：
- 在计算裁剪之后（操作已知裁剪影响）
- 在合并之前（确保每个操作都经过终结化）
- 在资源分配之前（可以标记待 IO 状态）

这个时机点是优化资源分配的最佳位置。

### 固定功能标志的演化

旧设计：`fixedFunctionFlags()` 返回位域
新设计：`usesMSAA()` 和 `usesStencil()` 独立方法

**演化原因**：
- 更清晰的语义（一个方法一个职责）
- 允许动态计算（不需要存储标志）
- 更好的类型安全

但为了兼容性，保留了旧接口作为默认实现。

### 调试断言策略

通过 `fAddDrawOpCalled` 标志验证操作生命周期：
```cpp
void validate() const override {
    SkASSERT(fAddDrawOpCalled);
}
```

捕获常见错误：操作创建后未添加到任务中。

### ClipResult 设计

`ClipResult` 枚举区分多种裁剪结果：
- **kFail**：需要标准裁剪
- **kClippedGeometrically**：几何裁剪，最优（无运行时开销）
- **kClippedInShader**：着色器裁剪，中等（片段着色器开销）
- **kClippedOut**：完全裁剪，最优（直接丢弃）

这种细粒度分类允许渲染管线做出最优决策。

## 性能考量

### 裁剪优化收益

几何裁剪（`kClippedGeometrically`）的优势：
- **零运行时开销**：裁剪在 CPU 完成
- **减少 overdraw**：只绘制可见像素
- **提高缓存效率**：更小的几何体

典型场景：矩形裁剪矩形、圆角矩形裁剪圆角矩形。

### 终结化时机优化

在终结化阶段标记待 IO 资源：
```cpp
texture->markPendingIO();
```

允许资源分配器：
- 更好地调度资源分配
- 重用即将释放的资源
- 避免不必要的拷贝

### MSAA 和模板查询缓存

`usesMSAA()` 和 `usesStencil()` 可能被多次调用：
- 裁剪计算时
- 管线状态设置时
- 合并决策时

子类应确保这些方法高效（内联、简单位检查等）。

### 固定功能标志开销

旧接口 `fixedFunctionFlags()` 返回位域，新接口使用独立方法：

**旧接口**：
```cpp
if (op->fixedFunctionFlags() & kUsesHWAA) { ... }
```

**新接口**：
```cpp
if (op->usesMSAA()) { ... }
```

新接口更清晰，编译器更容易内联优化。

### 裁剪失败的代价

当 `clipToShape()` 返回 `kFail` 时：
- 需要使用通用裁剪机制
- 可能需要剪刀测试（硬件开销）
- 可能需要着色器裁剪（片段着色器开销）
- 可能增加 overdraw

因此，实现 `clipToShape()` 优化是值得的（对于常见裁剪形状）。

### 调试开销隔离

调试验证代码仅在 `SK_DEBUG` 下编译：
```cpp
#ifdef SK_DEBUG
bool fAddDrawOpCalled = false;
void validate() const override { ... }
#endif
```

发布版本无任何开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrOp.h` | 继承 | 操作基类 |
| `src/gpu/ganesh/ops/GrMeshDrawOp.h` | 被继承 | 网格绘制操作基类 |
| `src/gpu/ganesh/GrProcessorSet.h` | 使用 | 处理器集合和分析 |
| `src/gpu/ganesh/GrAppliedClip.h` | 使用 | 应用的裁剪 |
| `src/gpu/ganesh/geometry/GrShape.h` | 使用 | 形状表示 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 协作 | 绘制上下文 |
| `src/gpu/ganesh/GrOpsTask.h` | 使用 | 任务管理 |
| `src/gpu/ganesh/ops/FillRectOp.h` | 被继承 | 矩形填充操作 |
| `src/gpu/ganesh/ops/FillRRectOp.h` | 被继承 | 圆角矩形填充操作 |
| `src/gpu/ganesh/ops/DrawableOp.h` | 被继承 | 自定义绘制操作 |
