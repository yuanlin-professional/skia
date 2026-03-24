# GrScissorState

> 源文件: [src/gpu/ganesh/GrScissorState.h](../../../../src/gpu/ganesh/GrScissorState.h)

## 概述

`GrScissorState` 是 Skia Ganesh GPU 后端中管理裁剪测试（scissor test）状态的类。裁剪测试是 GPU 渲染管线中的一项硬件功能，用于限制像素写入到屏幕的一个矩形区域内。`GrScissorState` 将裁剪矩形与渲染目标（render target）的尺寸绑定，提供了设置、交叉、放松和查询裁剪状态的完整接口。该类特别考虑了 Ganesh 中"近似匹配"（approximate-fit）渲染目标的特殊需求。

## 架构位置

`GrScissorState` 位于 Ganesh 渲染管线的裁剪处理阶段：

```
GrClip (Skia 裁剪栈)
  |
  v
GrAppliedClip (已应用裁剪)
  |
  +-- GrScissorState (硬件裁剪矩形)
  +-- GrWindowRectsState (窗口矩形裁剪)
  +-- GrFragmentProcessor (着色器裁剪)
  |
  v
GrOpsRenderPass (设置 GPU 裁剪状态)
  |
  v
GPU 硬件裁剪测试
```

`GrScissorState` 是 `GrAppliedClip` 的组成部分之一，在绘制命令提交到渲染通道时被用于配置 GPU 的硬件裁剪测试。

## 主要类与结构体

### `GrScissorState`

封装裁剪测试状态的值类型类。

**私有成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fRTSize` | `SkISize` | 渲染目标的后备存储尺寸（backing store dimensions） |
| `fRect` | `SkIRect` | 当前裁剪矩形 |

## 公共 API 函数

### 构造函数

```cpp
explicit GrScissorState(const SkISize& rtDims)
```

以给定的渲染目标尺寸创建一个禁用的裁剪状态（裁剪矩形等于整个渲染目标）。

### `void setDisabled()`

禁用裁剪测试，将裁剪矩形重置为整个渲染目标的范围。

### `bool set(const SkIRect& rect)`

设置裁剪矩形。先重置为全屏，再与给定矩形求交。返回值表示交集是否非空。

### `[[nodiscard]] bool intersect(const SkIRect& rect)`

将当前裁剪矩形与给定矩形求交。如果交集为空则将裁剪矩形设为空矩形并返回 `false`；否则返回 `true`。标记了 `[[nodiscard]]` 属性，要求调用者必须检查返回值。

### `bool relaxTest(const SkISize& logicalDimensions)`

针对近似匹配渲染目标的优化方法。如果当前裁剪矩形完全覆盖逻辑尺寸（但可能不覆盖后备存储的填充区域），则禁用裁剪并返回 `true`。这允许在"可以绘制到填充区域"的场景下消除不必要的裁剪测试。

- **参数：**
  - `logicalDimensions`：渲染目标的逻辑尺寸（必须 <= 后备存储尺寸）

### `bool enabled() const`

返回裁剪测试是否启用。当裁剪矩形严格小于渲染目标尺寸时返回 `true`。

### `const SkIRect& rect() const`

返回当前裁剪矩形的常引用。该矩形始终被包含在渲染目标边界内，或者为空矩形。

### 比较运算符

- **`bool operator==(const GrScissorState& other) const`**：比较两个裁剪状态是否相等（渲染目标尺寸和裁剪矩形均相同）。
- **`bool operator!=(const GrScissorState& other) const`**：不等比较。

## 内部实现细节

1. **裁剪矩形始终有效**：裁剪矩形始终被维护在渲染目标边界内（通过 `intersect` 操作保证），或者为空矩形。这个不变式通过 `enabled()` 和 `rect()` 中的 `SkASSERT` 进行验证。

2. **"禁用"状态的表示**：裁剪测试的"禁用"状态被表示为裁剪矩形等于整个渲染目标的范围（`SkIRect::MakeSize(fRTSize)`），而不是使用额外的布尔标志。这简化了交叉运算的逻辑。

3. **`enabled()` 的高效实现**：通过直接比较裁剪矩形的四条边与渲染目标尺寸来判断是否启用，避免了构造完整的 `SkIRect::MakeSize` 对象再调用 `contains()`。

4. **`set()` 方法的两步操作**：先调用 `setDisabled()` 重置为全屏，再调用 `intersect()` 将新矩形限制在渲染目标内。这确保了设置任意矩形时都能正确裁剪。

5. **近似匹配渲染目标的处理**：Ganesh 在分配渲染目标时可能使用"近似匹配"策略（分配略大于请求尺寸的表面以提高缓存复用率）。`relaxTest` 方法允许在填充区域可被写入的场景下移除裁剪限制。

## 依赖关系

- **`include/core/SkRect.h`**：提供 `SkIRect` 和 `SkISize` 类型

## 设计模式与设计决策

1. **不变式维护**：类始终维护裁剪矩形在渲染目标边界内的不变式，所有公共方法都在修改后保持这一约束。

2. **值语义**：`GrScissorState` 是一个值类型，支持拷贝和比较操作，便于在渲染状态中传递和缓存。

3. **显式构造函数**：使用 `explicit` 关键字防止从 `SkISize` 的隐式转换，要求调用者明确创建裁剪状态。

4. **`[[nodiscard]]` 标记**：`intersect()` 方法标记为 `[[nodiscard]]`，因为忽略返回值（是否交集为空）通常是一个编程错误。

5. **关于近似匹配的设计**：头文件注释详细解释了该类与近似匹配渲染目标的关系。当使用 stencil 时需要精确裁剪到逻辑边界以避免修改填充区域；而在纯颜色更新时可以通过 `relaxTest` 放松裁剪以获得更好性能。

## 性能考量

- **极小的内存占用**：仅包含一个 `SkISize`（8 字节）和一个 `SkIRect`（16 字节），总计约 24 字节。
- **`enabled()` 零开销**：直接进行四次整数比较，无需构造临时对象。
- **`relaxTest()` 消除裁剪开销**：在适用场景下禁用裁剪测试，避免 GPU 每像素的裁剪判断开销。
- **无堆分配**：所有数据存储在栈上，无动态内存分配。

## 相关文件

- `include/core/SkRect.h`：`SkIRect` 和 `SkISize` 类型定义
- `src/gpu/ganesh/GrAppliedClip.h`：已应用裁剪，包含 `GrScissorState`
- `src/gpu/ganesh/GrClip.h`：裁剪接口基类
- `src/gpu/ganesh/GrOpsRenderPass.h`：渲染通道，使用裁剪状态配置 GPU
- `src/gpu/ganesh/SurfaceDrawContext.h`：表面绘制上下文，管理裁剪状态
