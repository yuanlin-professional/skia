# GrOp

> 源文件
> - src/gpu/ganesh/ops/GrOp.h
> - src/gpu/ganesh/ops/GrOp.cpp

## 概述

`GrOp` 是 Ganesh GPU 后端中所有延迟 GPU 操作的抽象基类。为了便于重新排序和最小化绘制调用，Ganesh 不会在绘制调用时立即生成几何数据，而是捕获绘制参数，然后在刷新时生成几何数据。这使得 `GrOp` 子类可以完全自由地决定如何以及何时合并操作，以减少绘制调用和最小化状态更改。

该类实现了操作合并（merge）和链接（chain）机制。当两个操作合并时，一个操作接管联合数据，另一个被清空；当操作链接时，每个操作保留自己的数据但被链接成列表，头部操作负责执行整个链的工作。

## 架构位置

`GrOp` 位于 Ganesh 渲染管线的核心，是命令缓冲和执行层的基础：

- **上层**：由 `GrRenderTask` 和 `GrOpsTask` 管理和调度
- **同层**：与 `GrOpFlushState` 协作进行刷新，与 `GrCaps` 协作进行能力查询
- **下层**：通过 `GrGpu` 接口发出实际的 GPU 命令

在绘制流水线中，`GrOp` 是高层绘制调用和底层 GPU 命令之间的关键抽象层。

## 主要类与结构体

### GrOp 类层次结构

```
SkNoncopyable (私有继承)
    └── GrOp (抽象基类)
        ├── GrDrawOp (绘制操作)
        └── 其他特化操作
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fNextInChain` | `Owner` (unique_ptr) | 链中的下一个操作 |
| `fPrevInChain` | `GrOp*` | 链中的前一个操作 |
| `fClassID` | `const uint16_t` | 操作的类标识符，用于运行时类型识别 |
| `fBoundsFlags` | `uint16_t` | 边界标志（AA 扩展、零面积等） |
| `fUniqueID` | `mutable uint32_t` | 操作的唯一标识符，延迟初始化 |
| `fBounds` | `SkRect` | 操作的设备空间边界（不考虑裁剪） |
| `gCurrOpUniqueID` | `static atomic<uint32_t>` | 全局唯一 ID 计数器 |
| `gCurrOpClassID` | `static atomic<uint32_t>` | 全局类 ID 计数器 |

### 核心枚举类型

**CombineResult** - 操作合并结果：
- `kMerged`：操作已合并，被合并的操作应被销毁
- `kMayChain`：操作可以链接，调用者可选择是否链接
- `kCannotCombine`：操作无法合并

**HasAABloat** - 抗锯齿扩展标志：
- `kNo`：无抗锯齿扩展
- `kYes`：有抗锯齿扩展

**IsHairline** - 细线标志：
- `kNo`：非细线
- `kYes`：细线绘制（零面积）

## 公共 API 函数

### 工厂方法

```cpp
template<typename Op, typename... Args>
static Owner Make(GrRecordingContext* context, Args&&... args)
```
通用工厂方法，创建指定类型的操作。

```cpp
template<typename Op, typename... Args>
static Owner MakeWithExtraMemory(GrRecordingContext* context, size_t extraSize, Args&&... args)
```
创建带有额外内存的操作，适用于需要变长数据的操作。

### 操作合并与链接

```cpp
CombineResult combineIfPossible(GrOp* that, SkArenaAlloc* alloc, const GrCaps& caps)
```
尝试将另一个操作合并到当前操作中。只有相同类 ID 的操作才能合并。

```cpp
void chainConcat(GrOp::Owner next)
```
连接两个操作链。当前操作必须是尾部，传入的操作必须是头部。

```cpp
GrOp::Owner cutChain()
```
在当前操作之后切断链，返回后续的操作链。

### 执行生命周期

```cpp
void prePrepare(GrRecordingContext* context, const GrSurfaceProxyView& dstView,
                GrAppliedClip* clip, const GrDstProxyView& dstProxyView,
                GrXferBarrierFlags renderPassXferBarriers, GrLoadOp colorLoadOp)
```
在排序后、准备前调用的可选预准备步骤。

```cpp
void prepare(GrOpFlushState* state)
```
在执行前调用，操作应在此创建资源或传输数据。

```cpp
void execute(GrOpFlushState* state, const SkRect& chainBounds)
```
向 GrGpu 发出操作的命令。

### 边界管理

```cpp
const SkRect& bounds() const
```
返回操作的设备空间边界。

```cpp
void setClippedBounds(const SkRect& clippedBounds)
```
设置裁剪后的边界。

```cpp
bool hasAABloat() const
bool hasZeroArea() const
```
查询边界标志。

### 类型识别

```cpp
uint32_t classID() const
uint32_t uniqueID() const
```
获取类标识符和唯一标识符。

```cpp
template <typename T> const T& cast() const
template <typename T> T* cast()
```
安全的向下转型辅助方法。

### 链遍历

```cpp
GrOp* nextInChain() const
GrOp* prevInChain() const
bool isChainHead() const
bool isChainTail() const
```
操作链导航方法。

```cpp
template <typename OpSubclass = GrOp> class ChainRange
```
用于范围循环遍历操作链的辅助类。

## 内部实现细节

### ID 生成机制

类使用原子计数器生成唯一的类 ID 和操作 ID：

```cpp
static uint32_t GenID(std::atomic<uint32_t>* idCounter) {
    uint32_t id = idCounter->fetch_add(1, std::memory_order_relaxed);
    if (id == 0) {
        SK_ABORT("This should never wrap...");
    }
    return id;
}
```

类 ID 在子类静态初始化时生成（通过 `DEFINE_OP_CLASS_ID` 宏），而唯一 ID 延迟初始化以节省开销。

### 合并逻辑

合并过程首先检查类 ID 是否匹配，然后调用虚函数 `onCombineIfPossible`：

```cpp
GrOp::CombineResult GrOp::combineIfPossible(GrOp* that, SkArenaAlloc* alloc, const GrCaps& caps) {
    SkASSERT(this != that);
    if (this->classID() != that->classID()) {
        return CombineResult::kCannotCombine;
    }
    auto result = this->onCombineIfPossible(that, alloc, caps);
    if (result == CombineResult::kMerged) {
        this->joinBounds(*that);
    }
    return result;
}
```

合并成功后，边界会通过 `joinBounds` 合并。

### 链管理

操作链使用双向链表实现，使用 `unique_ptr` 管理下一个节点的所有权，原始指针指向前一个节点：

```cpp
void GrOp::chainConcat(GrOp::Owner next) {
    SkASSERT(next);
    SkASSERT(this->classID() == next->classID());
    SkASSERT(this->isChainTail());
    SkASSERT(next->isChainHead());
    fNextInChain = std::move(next);
    fNextInChain->fPrevInChain = this;
}
```

### 边界标志

边界标志使用位域存储：
- `kAABloat_BoundsFlag (0x1)`：几何体超出边界以确保抗锯齿覆盖
- `kZeroArea_BoundsFlag (0x2)`：细线或点（零面积几何体）
- `kUninitialized_BoundsFlag (0x4)`：调试用，标记未初始化

### 执行跟踪

所有执行函数都使用 `TRACE_EVENT0_ALWAYS` 进行性能跟踪：

```cpp
void GrOp::execute(GrOpFlushState* state, const SkRect& chainBounds) {
    TRACE_EVENT0_ALWAYS("skia.gpu", TRACE_STR_STATIC(name()));
    this->onExecute(state, chainBounds);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkMatrix`, `SkRect` | 几何变换和边界计算 |
| `GrSurfaceProxy` | 表面代理管理 |
| `GrCaps` | GPU 能力查询 |
| `GrOpFlushState` | 刷新状态管理 |
| `GrAppliedClip` | 裁剪应用 |
| `SkArenaAlloc` | 内存分配 |
| `GrRecordingContext` | 录制上下文 |

### 被依赖的模块

`GrOp` 是所有 Ganesh 操作的基类，被以下模块依赖：
- `GrDrawOp`：所有绘制操作的基类
- `GrMeshDrawOp`：网格绘制操作
- `FillRectOp`, `FillRRectOp`, `DrawableOp` 等：具体的绘制操作实现
- `GrOpsTask`：操作任务管理
- `GrOpFlushState`：刷新状态管理

## 设计模式与设计决策

### 模板方法模式

`GrOp` 使用模板方法模式，定义了操作的生命周期框架：
- 公共方法 `prepare()`, `execute()`, `combineIfPossible()` 定义算法骨架
- 纯虚函数 `onPrepare()`, `onExecute()`, `onCombineIfPossible()` 由子类实现

### 延迟执行策略

操作不立即执行而是被缓冲，这样做的优势：
1. **批处理优化**：相似操作可以合并，减少绘制调用
2. **重排序**：可以按状态分组，减少状态切换
3. **资源延迟分配**：只在真正需要时分配 GPU 资源

### 合并 vs 链接

设计提供两种组合策略：
- **合并（Merge）**：完全融合数据，减少操作数量，适合相似的绘制
- **链接（Chain）**：保持独立但共享执行，适合相关但不完全相同的操作

### 唯一 ID 延迟初始化

操作的唯一 ID 只在需要时才生成（主要用于审计追踪），这避免了大多数操作的不必要开销。

### 边界设计

操作的边界**必须**包含所有顶点的设备空间位置，且独立于裁剪。这确保裁剪元素可以正确应用，而边界本身不依赖裁剪。

### 类型安全的向下转型

使用 `cast<T>()` 方法配合 `ClassID()` 提供运行时类型检查的安全转型，比传统的 C++ RTTI 更高效。

## 性能考量

### 内存布局

- 使用 `uint16_t` 存储类 ID 和边界标志，节省内存
- 链表节点使用 `unique_ptr` 和原始指针混合，避免循环引用的同时保持所有权清晰
- 操作可以通过 `MakeWithExtraMemory` 预分配额外内存，避免额外堆分配

### 原子操作

ID 生成使用 `std::memory_order_relaxed`，因为只需要唯一性，不需要强同步保证。

### 内联和编译优化

- 小型访问器函数（如 `classID()`, `bounds()`）都是内联的
- `ChainRange` 迭代器设计支持编译器优化循环

### 调试开销隔离

- 使用条件编译（`#if GR_OP_SPEW`, `#if defined(GPU_TEST_UTILS)`）隔离调试代码
- `validate()` 和 `validateChain()` 只在 `SK_DEBUG` 下编译

### 合并优化

通过合并操作减少：
- GPU 命令数量
- 状态切换次数
- 驱动调用开销

典型场景：多个矩形填充可以合并为单个批次绘制。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrDrawOp.h` | 派生 | 绘制操作基类 |
| `src/gpu/ganesh/ops/GrMeshDrawOp.h` | 派生 | 网格绘制操作基类 |
| `src/gpu/ganesh/GrOpsTask.h` | 使用 | 操作任务管理 |
| `src/gpu/ganesh/GrOpFlushState.h` | 协作 | 刷新状态管理 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | GPU 能力查询 |
| `include/core/SkRect.h` | 依赖 | 边界矩形 |
| `include/core/SkMatrix.h` | 依赖 | 矩阵变换 |
| `src/core/SkArenaAlloc.h` | 依赖 | 内存分配器 |
