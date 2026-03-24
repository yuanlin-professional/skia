# GrDDLContext

> 源文件
> - src/gpu/ganesh/GrDDLContext.cpp

## 概述

`GrDDLContext` 是 Ganesh GPU 后端中用于 DDL（Deferred Display List，延迟显示列表）录制的专用上下文类。它是一个特殊的 `GrRecordingContext`，不依赖于实际的 GPU 设备（`GrGPU`），因此不能分配任何 GPU 资源。该上下文的主要目的是在 DDL 录制期间收集程序信息（`GrProgramInfo`），用于后续的预编译和优化。

DDL 技术允许在一个线程中录制渲染命令，然后在另一个线程（通常是主渲染线程）中执行，从而实现更好的多线程并行化。`GrDDLContext` 在录制阶段捕获所有需要的着色器程序配置，使得在回放阶段可以避免昂贵的着色器编译。

## 架构位置

在 Skia 的 Ganesh GPU 渲染架构中，`GrDDLContext` 位于上下文层次结构中：

```
GrContext_Base (基础上下文)
    └── GrRecordingContext (录制上下文)
        ├── GrDirectContext (直接上下文，有 GPU)
        └── GrDDLContext (DDL 录制上下文，无 GPU)
```

该类是录制上下文的特化，专门用于 DDL 工作流：

```
DDL 工作流
    1. GrDDLContext::recordProgramInfo() → 收集程序信息
    2. GrDDLContext::detachProgramData() → 提取程序数据
    3. 预编译着色器（可选）
    4. 在 GrDirectContext 上回放 DDL
```

## 主要类与结构体

### GrDDLContext

DDL 录制上下文的实现。

**继承关系：**
```
GrContext_Base (基础上下文)
    └── GrRecordingContext (录制上下文)
        └── GrDDLContext (DDL 上下文)
```

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fProgramInfoMap` | `ProgramInfoMap` | 存储录制期间遇到的唯一程序信息 |

### ProgramInfoMap

内部类，用于存储和管理程序描述符到程序信息的映射。

**类型定义：**
```cpp
typedef const GrProgramDesc  CacheKey;
typedef const GrProgramInfo* CacheValue;
```

**关键成员：**
- `fMap`: `SkLRUCache<CacheKey, CacheValue, DescHash>`，LRU 缓存实现

该映射使用程序描述符（`GrProgramDesc`）作为键，存储对应的程序信息指针。由于所有数据都存储在录制时的内存区域（arena），不需要引用计数或删除操作。

## 公共 API 函数

### 构造函数

```cpp
GrDDLContext(sk_sp<GrContextThreadSafeProxy> proxy)
    : INHERITED(std::move(proxy), true)
```

**功能：** 创建 DDL 录制上下文。

**参数：**
- `proxy`: 线程安全的上下文代理，包含共享的能力和配置

第二个参数 `true` 表示这是一个 DDL 上下文。

### 上下文放弃

```cpp
void abandonContext() override
```

**功能：** 放弃上下文资源。

该方法包含断言，因为在 DDL 录制器中放弃上下文没有太多意义（DDL 上下文本身就不拥有 GPU 资源）。实现调用基类的 `abandonContext()`，但这主要是为了完整性。

### 工厂方法（通过 GrRecordingContextPriv）

```cpp
sk_sp<GrRecordingContext> GrRecordingContextPriv::MakeDDL(sk_sp<GrContextThreadSafeProxy> proxy)
```

**功能：** 创建 DDL 录制上下文的静态工厂方法。

**实现：**
```cpp
sk_sp<GrRecordingContext> context(new GrDDLContext(std::move(proxy)));
if (!context->init()) {
    return nullptr;
}
return context;
```

该方法确保上下文正确初始化后才返回。

## 内部实现细节

### 程序信息录制

`recordProgramInfo()` 是 DDL 上下文的核心功能：

```cpp
void recordProgramInfo(const GrProgramInfo* programInfo) final
```

**工作流程：**
1. 检查 `programInfo` 是否为空
2. 获取上下文的能力（caps）
3. 检查后端是否支持 DDL（Metal 和 Direct3D 目前需要活动渲染目标）
4. 使用能力生成程序描述符（`GrProgramDesc`）
5. 验证描述符的有效性
6. 将描述符和程序信息添加到映射中

**后端限制：**
```cpp
if (this->backend() == GrBackendApi::kMetal || this->backend() == GrBackendApi::kDirect3D) {
    // Currently Metal and Direct3D require a live renderTarget to compute the key
    return;
}
```

Metal 和 Direct3D 后端需要实际的渲染目标来计算程序键，因此在这些后端上 DDL 的预编译功能受限。

### 程序数据分离

`detachProgramData()` 将收集的程序信息导出：

```cpp
void detachProgramData(TArray<ProgramData>* dst) final
```

该方法将内部映射的内容转换为 `ProgramData` 数组，调用者可以使用这些数据进行着色器预编译。

**断言检查：**
```cpp
SkASSERT(dst->empty());
```

确保目标数组是空的，避免数据丢失。

### ProgramInfoMap 实现

#### add 方法

```cpp
void add(CacheKey& desc, const GrProgramInfo* programInfo)
```

**功能：** 向映射中添加程序信息。

**实现：**
```cpp
SkASSERT(desc.isValid());
const CacheValue* preExisting = fMap.find(desc);
if (preExisting) {
    return;  // 已存在，不重复添加
}
fMap.insert(desc, programInfo);
```

该方法避免了重复的程序信息，确保每个唯一的程序配置只存储一次。

#### toArray 方法

```cpp
void toArray(TArray<ProgramData>* dst)
```

**功能：** 将映射内容转换为数组。

**实现：**
```cpp
fMap.foreach([dst](CacheKey* programDesc, CacheValue* programInfo) {
    dst->emplace_back(std::make_unique<const GrProgramDesc>(*programDesc),
                      *programInfo);
});
```

使用 `foreach` 遍历映射，为每个条目创建 `ProgramData` 对象。注意这里复制了程序描述符（`make_unique`），因为数据需要在映射之外的生命周期中存在。

#### DescHash 实现

```cpp
struct DescHash {
    uint32_t operator()(CacheKey& desc) const {
        return SkChecksum::Hash32(desc.asKey(), desc.keyLength());
    }
};
```

该哈希函数用于在 LRU 缓存中快速查找程序描述符，使用 Skia 的校验和算法计算哈希值。

### LRU 缓存使用

映射使用 `SkLRUCache` 而非普通的哈希表：
```cpp
SkLRUCache<CacheKey, CacheValue, DescHash> fMap;
```

虽然在 DDL 上下文中不太可能达到缓存容量限制，但 LRU 缓存提供了：
- 高效的查找（O(1) 平均时间）
- 自动容量管理（如果需要）
- 与其他 Skia 缓存一致的接口

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrRecordingContext` | 基类，提供录制上下文基础设施 |
| `GrContextThreadSafeProxy` | 线程安全的上下文代理 |
| `GrCaps` | GPU 能力查询 |
| `GrProgramDesc` | 程序描述符，着色器缓存键 |
| `GrProgramInfo` | 完整的程序配置信息 |
| `SkLRUCache` | LRU 缓存实现 |
| `SkChecksum` | 校验和和哈希函数 |
| `GrRecordingContextPriv` | 私有接口，提供工厂方法 |

### 被依赖的模块

`GrDDLContext` 被以下组件使用：

| 模块 | 使用方式 |
|------|---------|
| `SkDeferredDisplayListRecorder` | 创建和管理 DDL 上下文 |
| DDL 录制 API | 通过录制器使用上下文 |
| 着色器预编译系统 | 使用收集的程序信息 |

## 设计模式与设计决策

### 特化上下文模式

`GrDDLContext` 是 `GrRecordingContext` 的特化实现，专门用于 DDL 工作流。这种设计允许：
- 代码复用（继承通用录制逻辑）
- 特定行为（覆盖 `recordProgramInfo` 和 `detachProgramData`）
- 类型安全（明确的 DDL 语义）

### 无 GPU 设计

该上下文故意不关联 `GrGpu` 对象，强制其不能执行实际的 GPU 操作。这确保了：
- 线程安全（无 GPU 状态竞争）
- 清晰的职责分离（录制 vs 执行）
- 更好的多线程性能

### 程序信息收集

通过覆盖 `recordProgramInfo()`，该类在录制期间透明地收集着色器信息。这是观察者模式的一种形式，录制操作触发程序信息的收集。

### 延迟分配策略

程序信息指针存储在录制时的内存区域（arena）中，不需要引用计数或复制。这是一种高效的内存管理策略，假设数据在录制会话结束前保持有效。

### 两阶段数据传递

设计采用两阶段方法：
1. **录制阶段**：`recordProgramInfo()` 收集数据
2. **分离阶段**：`detachProgramData()` 导出数据

这种分离允许在录制完成后灵活处理收集的数据。

## 性能考量

### 避免重复存储

`ProgramInfoMap::add()` 检查重复，确保每个唯一的程序配置只存储一次。这减少了内存使用和后续处理时间。

### 哈希查找

使用哈希表（通过 `SkLRUCache`）实现 O(1) 平均时间的查找，即使在有大量不同着色器配置的复杂场景中也能保持高效。

### 最小化分配

程序信息指针直接存储，不复制实际的程序数据。只有在 `toArray()` 中才复制程序描述符，且只复制一次。

### LRU 缓存开销

虽然使用 LRU 缓存，但在典型的 DDL 录制场景中，条目数量不会达到需要驱逐的程度。LRU 维护的开销（双向链表）是可接受的。

### 后端特定优化

通过检测不支持 DDL 的后端（Metal、Direct3D），避免不必要的工作。这些检查在 `recordProgramInfo()` 的早期阶段进行，最小化开销。

### 内存区域分配

假设程序信息存储在录制时的内存区域中，避免了引用计数和内存管理的开销。这是一种"bump allocator"策略，非常高效。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/ganesh/GrRecordingContext.h` | 基类 | 录制上下文接口 |
| `include/gpu/ganesh/GrContextThreadSafeProxy.h` | 依赖 | 线程安全代理 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | GPU 能力 |
| `src/gpu/ganesh/GrProgramDesc.h` | 依赖 | 程序描述符 |
| `src/gpu/ganesh/GrProgramInfo.h` | 依赖 | 程序信息 |
| `src/core/SkLRUCache.h` | 依赖 | LRU 缓存实现 |
| `src/core/SkChecksum.h` | 依赖 | 哈希函数 |
| `src/gpu/ganesh/GrRecordingContextPriv.h` | 依赖 | 私有接口 |
| `include/core/SkDeferredDisplayListRecorder.h` | 使用者 | DDL 录制器 |
