# GrResourceAllocator

> 源文件
> - src/gpu/ganesh/GrResourceAllocator.h
> - src/gpu/ganesh/GrResourceAllocator.cpp

## 概述

`GrResourceAllocator` 是 Skia Ganesh GPU 后端中负责在 flush 时显式分配 GPU 资源的核心组件。它通过接收 surface proxy 的使用时间区间,使用类似寄存器分配的算法来优化 GPU 内存的分配和复用,以减少内存占用并提高性能。该分配器采用三阶段工作流程:收集使用区间、规划分配方案、执行实际分配,支持资源回收和预算管理。

## 架构位置

在 Skia GPU 架构中,`GrResourceAllocator` 位于渲染任务执行和资源管理之间的关键位置:

```
GrDirectContext
    └── GrDrawingManager
        └── GrResourceAllocator (在 flush 时调用)
            ├── 输入: OpsTask 收集的 proxy 使用区间
            ├── 与 GrResourceProvider 交互获取/创建资源
            ├── 与 GrResourceCache 交互管理预算
            └── 输出: 实例化后的 surface 分配给 proxy
```

该类在渲染流水线中扮演内存优化器的角色,在绘制命令提交到 GPU 之前确定资源分配策略。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `GrResourceAllocator` | 无 | 主类,负责资源分配的全流程管理 |
| `GrResourceAllocator::Interval` | 无 | 表示一个 proxy 的使用时间区间 |
| `GrResourceAllocator::Register` | 无 | 代表一个未来会使用的 surface(类似寄存器) |
| `GrResourceAllocator::IntervalList` | 无 | 管理按特定顺序排序的区间链表 |

### GrResourceAllocator 关键成员变量

| 成员变量 | 类型 | 作用 |
|---------|------|------|
| `fDContext` | `GrDirectContext*` | 指向 Direct Context,用于访问资源提供者 |
| `fIntvlList` | `IntervalList` | 所有区间按起始时间排序的列表 |
| `fActiveIntvls` | `IntervalList` | 当前活跃的区间,按结束时间排序 |
| `fFinishedIntvls` | `IntervalList` | 已完成的区间,按起始时间排序 |
| `fFreePool` | `FreePoolMultiMap` | 可复用的 Register 池 |
| `fUniqueKeyRegisters` | `UniqueKeyRegisterHash` | 拥有唯一键的 Register 映射表 |
| `fIntvlHash` | `IntvlHash` | 按 proxy ID 索引的区间哈希表 |
| `fNumOps` | `unsigned int` | 操作计数器,用于标记时间点 |
| `fFailedInstantiation` | `bool` | 标记是否发生实例化失败 |

### Interval 关键成员

| 成员变量 | 类型 | 作用 |
|---------|------|------|
| `fProxy` | `GrSurfaceProxy*` | 关联的 surface proxy |
| `fStart/fEnd` | `unsigned int` | 使用区间的开始和结束时间 |
| `fRegister` | `Register*` | 分配的寄存器 |
| `fUses` | `unsigned int` | 引用计数 |
| `fAllowRecycling` | `AllowRecycling` | 是否允许回收 |

### Register 关键成员

| 成员变量 | 类型 | 作用 |
|---------|------|------|
| `fOriginatingProxy` | `GrSurfaceProxy*` | 起源的 proxy,用于缓存分配 |
| `fScratchKey` | `skgpu::ScratchKey` | scratch 资源的键 |
| `fExistingSurface` | `sk_sp<GrSurface>` | 从缓存中找到的现有 surface |
| `fAccountedForInBudget` | `bool` | 是否已计入预算 |

## 公共 API 函数

### 核心操作函数

```cpp
// 添加 proxy 的使用区间
void addInterval(GrSurfaceProxy* proxy, unsigned int start, unsigned int end,
                 ActualUse actualUse, AllowRecycling allowRecycling);

// 规划分配方案(第一阶段)
bool planAssignment();

// 检查预算是否足够并清理空间(第二阶段)
bool makeBudgetHeadroom();

// 执行实际的资源分配(第三阶段)
bool assign();

// 重置分配器状态
void reset();
```

### 辅助函数

```cpp
// 获取当前操作索引
unsigned int curOp() const;

// 递增操作计数器
void incOps();

// 检查是否发生实例化失败
bool failedInstantiation() const;
```

## 内部实现细节

### 资源分配算法

分配器采用线性扫描的寄存器分配算法:

1. **区间收集阶段** (`addInterval`):
   - 为每个 proxy 创建或扩展使用区间
   - 只读的 lazy proxy 立即实例化
   - 区间按起始时间插入排序链表

2. **规划阶段** (`planAssignment`):
   - 线性扫描所有区间,维护活跃区间列表
   - 为每个非 lazy proxy 查找或创建 Register
   - 实例化 fully-lazy proxy 以获取精确大小
   - 过期的区间将 Register 归还到自由池

3. **预算检查阶段** (`makeBudgetHeadroom`):
   - 计算需要的额外内存
   - 请求资源缓存清理足够空间
   - 失败时返回 false,允许外部重试

4. **分配阶段** (`assign`):
   - 实例化剩余的 lazy proxy
   - 通过 Register 为 proxy 创建或分配 surface
   - 任何失败都会设置 `fFailedInstantiation` 标志

### 关键优化机制

**资源复用策略**:
```cpp
bool Register::isRecyclable(const GrCaps& caps, GrSurfaceProxy* proxy,
                            int knownUseCount, AllowRecycling allowRecycling)
```
只有满足以下条件的 Register 才能被回收:
- 允许回收标志为 kYes
- GPU 支持 scratch texture 复用或是 render target
- 拥有有效的 scratch key(不是 unique key)
- proxy 的引用计数不超过已知使用次数

**自由池管理**:
- 使用 `SkTMultiMap` 按 scratch key 索引可复用的 Register
- `findOrCreateRegisterFor` 优先从自由池查找匹配的 Register
- `expire` 函数在区间结束时将可回收的 Register 加入自由池

**Lazy Proxy 处理**:
- **只读 lazy proxy**: 在 `addInterval` 时立即实例化
- **Fully-lazy proxy**: 在 `planAssignment` 时实例化以获取大小
- **Partially-lazy proxy**: 在 `assign` 时实例化

### 特殊场景处理

**Vulkan Secondary Command Buffer 支持**:
当 `AllowRecycling::kNo` 时,禁止 Register 回收,因为在 secondary command buffer 中采样的 offscreen surface 必须保持独立分配,避免后续复用覆盖早期内容。

**预算超限处理**:
- `makeBudgetHeadroom` 计算所需的额外内存
- 请求资源缓存执行 `purgeToMakeHeadroom`
- 如果无法获取足够空间,返回 false

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrDirectContext` | 访问资源提供者和 caps |
| `GrResourceProvider` | 查找和创建 GPU 资源 |
| `GrResourceCache` | 预算管理和资源清理 |
| `GrSurfaceProxy` | 操作的目标对象 |
| `GrCaps` | 查询 GPU 能力(如 scratch 复用支持) |
| `skgpu::ScratchKey/UniqueKey` | 资源键管理 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrDrawingManager` | 在 flush 时调用分配器进行资源分配 |
| `OpsTask` | 收集并提供 proxy 使用区间信息 |
| `GrRenderTask` | 通过 OpsTask 间接使用 |

## 设计模式与设计决策

### 设计模式

1. **寄存器分配算法**: 借鉴编译器优化中的寄存器分配思想,将 GPU surface 视为"寄存器",通过分析生命周期实现复用。

2. **三阶段流程**:
   - **Plan**: 只做规划,不实际分配,可以回滚
   - **MakeBudgetHeadroom**: 预算检查点,允许清理和重试
   - **Assign**: 最终提交,不可逆

3. **对象池模式**: Register 自由池避免重复创建对象。

4. **惰性求值**: Lazy proxy 延迟实例化,按需获取资源。

### 关键设计决策

**为何使用区间而非依赖图**:
- 区间表示更简单,易于排序和管理
- 线性扫描算法效率高,时间复杂度 O(n)
- 通过操作索引自然表达时间顺序

**为何分离规划和执行**:
- 允许在实际分配前评估内存需求
- 支持预算检查和资源清理
- 失败后可以重新规划(例如改变 DAG 顺序)

**使用 Arena 分配器**:
```cpp
SkSTArenaAllocWithReset<kInitialArenaSize> fInternalAllocator;
```
- Interval 和 Register 生命周期与分配器相同
- 避免频繁的小对象分配/释放
- `reset()` 时统一释放所有内存

## 性能考量

### 内存优化

1. **表面复用**: 通过自由池机制,多个不重叠的 proxy 可以共享同一个 GPU surface。
2. **紧凑分配**: 尽量减少同时存活的 surface 数量。
3. **预算管理**: 在分配前主动清理缓存,避免 OOM。

### 时间复杂度

- **添加区间**: O(n),需要在排序链表中插入
- **规划分配**: O(n + m),n 为区间数,m 为活跃区间数
- **执行分配**: O(n),线性扫描完成区间

### 优化技巧

**排序链表插入优化**:
```cpp
// 83% 的情况直接追加到尾部
if (fTail->start() <= intvl->start()) {
    fTail->setNext(intvl);
    fTail = intvl;
}
```

**批量清理**: `expire` 函数批量处理过期区间,避免逐个检查。

**缓存友好**: Arena 分配器保证对象在内存中连续,提高缓存命中率。

### 性能权衡

- **灵活性 vs 确定性**: 支持 lazy proxy 增加了灵活性,但也增加了失败处理的复杂性。
- **复用 vs 管理开销**: 自由池机制提升复用率,但维护哈希表和链表有开销。
- **三阶段 vs 一次性**: 多阶段流程允许更好的错误处理和优化,但增加了调用复杂度。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrResourceProvider.h` | 依赖 | 资源创建和查找接口 |
| `src/gpu/ganesh/GrResourceCache.h` | 依赖 | 资源缓存和预算管理 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 操作对象 | 被分配资源的代理对象 |
| `src/gpu/ganesh/GrDrawingManager.cpp` | 使用者 | 调用分配器执行资源分配 |
| `src/gpu/ganesh/GrOpsTask.cpp` | 数据提供者 | 收集 proxy 使用区间 |
| `src/gpu/ganesh/GrCaps.h` | 查询能力 | GPU 能力查询接口 |
| `src/gpu/ResourceKey.h` | 资源键 | Scratch 和 Unique key 定义 |
