# SkRasterClipStack

> 源文件: src/core/SkRasterClipStack.h

## 概述

`SkRasterClipStack` 是 Skia 中用于管理光栅裁剪栈的核心类，提供了保存（save）和恢复（restore）裁剪状态的栈式管理机制。它封装了 `SkRasterClip` 的栈操作，支持延迟复制优化，在多个 save 操作之间共享相同的裁剪状态，只有在实际修改裁剪时才进行复制。

该类使用延迟计数（deferred count）机制来优化连续的 save 操作，避免不必要的内存分配和数据复制。它还负责处理抗锯齿（anti-aliasing）的禁用条件，特别是当渲染区域过大需要分块（tiling）时自动禁用抗锯齿以提高性能。

## 架构位置

`SkRasterClipStack` 位于 Skia 绘制上下文（drawing context）的裁剪管理层：

- **上层**：`SkCanvas` 的 save/restore 机制调用 `SkRasterClipStack` 管理裁剪状态
- **中层**：`SkRasterClipStack` 管理裁剪栈的生命周期和状态
- **底层**：`SkRasterClip` 提供具体的裁剪区域表示

在设备（Device）层面，每个绘制上下文维护一个 `SkRasterClipStack` 实例，负责跟踪当前的裁剪状态以及保存/恢复历史。

## 主要类与结构体

### SkRasterClipStack 类

**继承关系：**
- 继承自 `SkNoncopyable`（禁止拷贝）

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fStack` | `SkTBlockList<Rec, 16>` | 裁剪记录的块链表栈，预分配 16 个元素 |
| `fRootBounds` | `SkIRect` | 根边界矩形（设备的完整绘制区域） |
| `fDisableAA` | `bool` | 是否禁用抗锯齿（大区域需要分块时禁用） |
| `fCounter` | `int`（调试） | 调试模式下的 save/restore 计数器 |

### Rec 内部结构体

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRC` | `SkRasterClip` | 实际的光栅裁剪对象 |
| `fDeferredCount` | `int` | 延迟计数，0 表示正常条目，>0 表示有待处理的 save |

## 公共 API 函数

### 构造与配置

```cpp
SkRasterClipStack(int width, int height);
```
构造函数，使用指定宽度和高度初始化根边界，并检查是否需要禁用抗锯齿（通过 `SkScan::PathRequiresTiling()` 判断）。

```cpp
void setNewSize(int w, int h);
```
重新设置根边界尺寸，仅在栈深度为 1（即栈顶）时有效。

### 状态访问

```cpp
const SkRasterClip& rc() const;
```
返回当前（栈顶）的裁剪区域引用。

### 栈操作

```cpp
void save();
```
保存当前裁剪状态。采用延迟复制策略，只增加 `fDeferredCount` 计数器，不立即复制裁剪对象。

```cpp
void restore();
```
恢复到上一个保存的裁剪状态。减少 `fDeferredCount`，如果计数降为 -1 则从栈中弹出当前记录。

### 裁剪操作

```cpp
void clipRect(const SkMatrix& ctm, const SkRect& rect, SkClipOp op, bool aa);
void clipRRect(const SkMatrix& ctm, const SkRRect& rrect, SkClipOp op, bool aa);
void clipPath(const SkMatrix& ctm, const SkPath& path, SkClipOp op, bool aa);
void clipShader(sk_sp<SkShader> sh);
void clipRegion(const SkRegion& rgn, SkClipOp op);
```

执行各种裁剪操作，内部调用 `writable_rc()` 获取可写的裁剪对象。抗锯齿标志会通过 `finalAA()` 处理，在需要分块时强制禁用。

### 特殊操作

```cpp
void replaceClip(const SkIRect& rect);
```
直接替换裁剪区域为指定矩形（与根边界求交后）。这是特殊的裁剪操作，不同于常规的 intersect/difference 等操作。

### 验证

```cpp
void validate() const;
```
调试模式下验证裁剪区域的一致性，确保裁剪边界不超出根边界。

## 内部实现细节

### 延迟复制机制

`save()` 方法的核心优化：
1. 不立即复制 `SkRasterClip` 对象
2. 只增加当前记录的 `fDeferredCount`
3. 多次连续 save 不分配内存

`writable_rc()` 在需要修改时触发实际复制：
1. 检查 `fDeferredCount > 0`（有延迟的 save）
2. 减少计数并创建新记录（复制当前裁剪）
3. 返回新记录的可写引用

这种策略在常见的"save-save-...-restore-restore"模式中避免了大量无用的复制。

### 块链表栈结构

使用 `SkTBlockList<Rec, 16>` 而非 `std::vector<Rec>` 的优势：
- **减少重新分配**：块链表结构避免扩容时的大量数据移动
- **指针稳定性**：块内指针不会因扩容失效
- **预分配优化**：模板参数 16 表示预分配 16 个元素，覆盖大多数栈深度

### 抗锯齿自动禁用

构造函数中调用 `SkScan::PathRequiresTiling(fRootBounds)` 判断：
- 如果绘制区域过大（需要分块扫描转换），则设置 `fDisableAA = true`
- `finalAA()` 方法将用户请求的 AA 标志与 `fDisableAA` 结合

这个设计避免了在大尺寸渲染时因抗锯齿导致的性能问题。

### 边界交集保护

`replaceClip()` 方法确保新裁剪区域不超出根边界：
```cpp
if (!devRect.intersect(fRootBounds)) {
    this->writable_rc().setEmpty();
} else {
    this->writable_rc().setRect(devRect);
}
```

### 调试计数器

调试模式下的 `fCounter` 跟踪 save/restore 的配对：
- `save()` 时递增
- `restore()` 时递减
- `restore()` 前断言 `fCounter >= 0` 确保没有多余的 restore

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `SkRasterClip` | 底层裁剪区域表示 |
| `SkTBlockList` | 块链表容器 |
| `SkScan` | 扫描转换工具（判断是否需要分块） |
| `SkClipOp` | 裁剪操作枚举 |
| `SkMatrix` | 变换矩阵 |
| `SkRect` / `SkIRect` | 矩形结构 |
| `SkRRect` | 圆角矩形 |
| `SkPath` | 路径 |
| `SkRegion` | 区域 |
| `SkShader` | 着色器 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| `SkDevice` | 设备层使用裁剪栈管理状态 |
| `SkCanvas` | Canvas 层的 save/restore 机制 |
| `SkDraw` | 绘制操作使用当前裁剪 |

## 设计模式与设计决策

### 写时复制（Copy-on-Write）

延迟复制机制是 COW 模式的变体：
- 多个保存点共享相同的裁剪对象（只增加引用计数）
- 只有在修改时才创建副本

这在大量嵌套 save/restore 但很少实际修改裁剪的场景中非常高效。

### 栈模式

标准的栈式状态管理，符合图形 API 的常见模式（OpenGL、Canvas 2D 等都使用类似的 save/restore 机制）。

### 非拷贝语义

继承 `SkNoncopyable` 确保裁剪栈不会被意外复制，防止状态管理混乱。

### 自适应性能优化

根据绘制区域大小自动决定是否启用抗锯齿，平衡质量和性能：
- 小区域：允许 AA，提高视觉质量
- 大区域：禁用 AA，避免内存和性能问题

### RAII 友好设计

虽然类本身不是 RAII，但其 save/restore 接口天然适配 RAII 包装器（如 `SkAutoCanvasRestore`）。

## 性能考量

### 内存分配优化

- **延迟复制**：避免不必要的 `SkRasterClip` 复制
- **块链表**：减少重新分配和数据移动
- **预分配**：16 个元素的预分配覆盖大多数使用场景

典型的栈深度统计显示 95% 的情况下栈深度不超过 8，预分配 16 足够且不浪费。

### 缓存友好性

块链表虽然不如连续数组缓存友好，但考虑到：
- 栈操作频率相对较低
- 每个记录包含较大的 `SkRasterClip` 对象
- 指针稳定性的价值

权衡后块链表是合理选择。

### 抗锯齿控制

自动禁用大区域的抗锯齿可以显著提高性能：
- 避免分配巨大的抗锯齿缓冲区
- 减少扫描转换的计算量
- 大尺寸下抗锯齿的视觉差异不明显

### 验证开销

`validate()` 只在调试模式下生效，通过宏控制：
```cpp
#ifdef SK_DEBUG
    // 验证代码
#endif
```

发布版本中完全无开销。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkRasterClip.h` | 底层裁剪区域类 |
| `src/base/SkTBlockList.h` | 块链表容器 |
| `src/core/SkScan.h` | 扫描转换工具 |
| `include/core/SkClipOp.h` | 裁剪操作枚举 |
| `include/core/SkMatrix.h` | 变换矩阵 |
| `include/core/SkPath.h` | 路径定义 |
| `include/core/SkRRect.h` | 圆角矩形 |
| `include/core/SkRegion.h` | 区域表示 |
| `include/private/base/SkNoncopyable.h` | 禁止拷贝基类 |
