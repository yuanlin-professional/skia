# GrGpuResource

> 源文件: src/gpu/ganesh/GrGpuResource.h, src/gpu/ganesh/GrGpuResource.cpp

## 概述

`GrGpuResource` 是 Skia Ganesh GPU 后端中用于管理可缓存 GPU 资源的核心基类。它实现了复杂的资源缓存机制,支持 Scratch Key 和 Unique Key 两种键值系统,并与 `GrResourceCache` 紧密集成,提供自动化的资源生命周期管理和内存预算控制。

该类通过 CRTP (Curiously Recurring Template Pattern) 实现的 `GrIORef` 基类提供双重引用计数:常规引用计数和命令缓冲区使用计数,确保资源在所有引用释放前不会被销毁。

主要功能:
- 支持可预算 (budgeted) 和不可预算资源管理
- 实现 Scratch Key 机制用于资源复用
- 支持 Unique Key 实现资源去重和查找
- 与 GrResourceCache 协同实现 LRU 缓存策略
- 集成内存追踪和调试支持

## 架构位置

`GrGpuResource` 位于 Ganesh GPU 后端的资源管理核心层,处于以下架构位置:

1. **资源层次**
   - `GrIORef<GrGpuResource>` (基类): 提供引用计数机制
   - `GrGpuResource` (当前类): 添加缓存和键值管理
   - 派生类: `GrGpuBuffer`, `GrRenderTarget`, `GrTexture` 等具体资源类型

2. **系统集成**
   - 与 `GrResourceCache` 紧密协作,实现缓存策略
   - 通过 `GrGpu` 访问底层 GPU 驱动
   - 被 `GrSurfaceProxy` 引用,支持延迟资源分配
   - 参与 `GrDirectContext` 的资源管理

3. **关键接口**
   - `CacheAccess`: 授予 `GrResourceCache` 特权访问
   - `ResourcePriv`: 提供内部代码的特权操作
   - `ProxyAccess`: 支持 `GrSurfaceProxy` 的零引用到一引用转换

## 主要类与结构体

### 继承关系

```
SkNoncopyable
    └── GrIORef<GrGpuResource>
            └── GrGpuResource
                    ├── GrGpuBuffer
                    ├── GrRenderTarget
                    ├── GrTexture
                    └── GrAttachment
```

### GrIORef 关键成员

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRefCnt` | `std::atomic<int32_t>` | 主引用计数 |
| `fCommandBufferUsageCnt` | `std::atomic<int32_t>` | 命令缓冲区使用计数 |

### GrGpuResource 关键成员

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrGpu*` | 指向 GPU 对象的非拥有指针 |
| `fGpuMemorySize` | `size_t` | 资源占用的 GPU 内存大小(字节) |
| `fUniqueID` | `UniqueID` | 资源的全局唯一 ID |
| `fUniqueKey` | `skgpu::UniqueKey` | 用于去重和查找的唯一键 |
| `fScratchKey` | `skgpu::ScratchKey` | 用于资源复用的临时键 |
| `fBudgetedType` | `GrBudgetedType` | 预算类型(可预算/不可预算) |
| `fRefsWrappedObjects` | `bool` | 是否引用外部包装对象 |
| `fCacheArrayIndex` | `int` | 在缓存中的数组/堆索引 |
| `fTimestamp` | `uint32_t` | 最近访问时间戳 |
| `fTimeWhenBecamePurgeable` | `time_point` | 变为可清除状态的时间点 |
| `fLabel` | `std::string` | 资源标签(用于调试) |

### GrBudgetedType 枚举

```cpp
enum class GrBudgetedType {
    kBudgeted,                // 计入预算
    kUnbudgetedCacheable,     // 不计入预算但可缓存(包装资源)
    kUnbudgetedUncacheable    // 不可缓存
};
```

## 公共 API 函数

### 资源状态查询

```cpp
// 检查资源是否已被销毁或放弃
bool wasDestroyed() const;

// 获取拥有该资源的 GrDirectContext
const GrDirectContext* getContext() const;
GrDirectContext* getContext();

// 获取 GPU 内存占用(字节)
size_t gpuMemorySize() const;

// 获取资源的全局唯一 ID
UniqueID uniqueID() const;

// 获取资源的 Unique Key
const skgpu::UniqueKey& getUniqueKey() const;

// 获取/设置资源标签
std::string getLabel() const;
void setLabel(std::string_view label);
```

### 引用计数管理 (GrIORef)

```cpp
// 检查是否只有一个引用
bool unique() const;

// 增加主引用计数
void ref() const;

// 减少主引用计数
void unref() const;

// 增加命令缓冲区使用计数
void refCommandBuffer() const;

// 减少命令缓冲区使用计数
void unrefCommandBuffer() const;
```

### 特权访问接口

```cpp
// 获取 CacheAccess 对象(供 GrResourceCache 使用)
CacheAccess cacheAccess();
const CacheAccess cacheAccess() const;

// 获取 ResourcePriv 对象(供内部代码使用)
ResourcePriv resourcePriv();
const ResourcePriv resourcePriv() const;

// 获取 ProxyAccess 对象(供 GrSurfaceProxy 使用)
ProxyAccess proxyAccess();
```

### 虚函数接口

```cpp
// 子类必须实现:返回资源类型名称
virtual const char* getResourceType() const = 0;

// 转储内存统计信息到追踪系统
virtual void dumpMemoryStatistics(SkTraceMemoryDump* traceMemoryDump) const;

// 释放 GPU 资源(子类重写)
virtual void onRelease();

// 放弃 GPU 资源(上下文丢失时调用,子类重写)
virtual void onAbandon();

// 计算 GPU 内存占用(子类必须实现)
virtual size_t onGpuMemorySize() const = 0;

// 设置标签后的回调(子类重写)
virtual void onSetLabel() = 0;

// 计算 Scratch Key(子类可重写)
virtual void computeScratchKey(skgpu::ScratchKey*) const;
```

## 内部实现细节

### 双重引用计数机制

`GrIORef` 实现了两套独立的引用计数:

1. **主引用计数 (`fRefCnt`)**
   - 表示外部持有者的引用
   - 归零时触发 `notifyARefCntIsZero(kMainRef)`

2. **命令缓冲区使用计数 (`fCommandBufferUsageCnt`)**
   - 追踪资源在命令缓冲区中的使用
   - 归零时触发 `notifyARefCntIsZero(kCommandBufferUsage)`
   - 防止资源在命令提交前被释放

### 资源注册流程

资源必须在构造完成后立即注册到缓存:

```cpp
// 非包装资源
void registerWithCache(skgpu::Budgeted budgeted) {
    fBudgetedType = budgeted ? kBudgeted : kUnbudgetedUncacheable;
    computeScratchKey(&fScratchKey);  // 计算 Scratch Key
    cache->insertResource(this);       // 插入缓存
}

// 包装资源
void registerWithCacheWrapped(GrWrapCacheable wrapType) {
    fBudgetedType = (wrapType == kYes) ? kUnbudgetedCacheable
                                       : kUnbudgetedUncacheable;
    fRefsWrappedObjects = true;
    cache->insertResource(this);
}
```

### 引用计数归零处理

```cpp
void notifyARefCntIsZero(LastRemovedRef removedRef) const {
    if (wasDestroyed()) {
        // 已从缓存移除,检查是否可以删除
        if (!hasRef() && hasNoCommandBufferUsages()) {
            delete this;
        }
        return;
    }
    // 通知缓存处理引用计数归零事件
    cache->notifyARefCntReachedZero(this, removedRef);
}
```

### Scratch Key 与 Unique Key 管理

1. **Scratch Key**
   - 由 `computeScratchKey()` 在注册时自动计算
   - 用于查找可复用的资源
   - 只有 `kBudgeted` 资源可以作为 Scratch 资源

2. **Unique Key**
   - 通过 `setUniqueKey()` 显式设置
   - 实现资源去重和精确查找
   - 设置后资源从 Scratch 池转为 Unique 池
   - 包装资源的 Unique Key 提供弱引用机制

### 预算类型转换

```cpp
// 转为可预算(仅限非包装资源)
void makeBudgeted() {
    if (fBudgetedType == kUnbudgetedUncacheable && !fRefsWrappedObjects) {
        fBudgetedType = kBudgeted;
        cache->didChangeBudgetStatus(this);
    }
}

// 转为不可预算(仅限无 Unique Key 的资源)
void makeUnbudgeted() {
    if (fBudgetedType == kBudgeted && !fUniqueKey.isValid()) {
        fBudgetedType = kUnbudgetedUncacheable;
        cache->didChangeBudgetStatus(this);
    }
}
```

### 资源清理流程

```cpp
// 正常释放
void release() {
    onRelease();                   // 子类释放 GPU 资源
    cache->removeResource(this);   // 从缓存移除
    fGpu = nullptr;                // 清空 GPU 指针
    fGpuMemorySize = 0;
}

// 上下文丢失时放弃
void abandon() {
    onAbandon();                   // 子类放弃 GPU 句柄
    cache->removeResource(this);   // 从缓存移除
    fGpu = nullptr;
    fGpuMemorySize = 0;
}
```

### UniqueID 生成

```cpp
uint32_t GrGpuResource::CreateUniqueID() {
    static std::atomic<uint32_t> nextID{1};
    uint32_t id;
    do {
        id = nextID.fetch_add(1, std::memory_order_relaxed);
    } while (id == SK_InvalidUniqueID);  // 跳过无效 ID
    return id;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrResourceCache` | 资源缓存管理器 |
| `GrGpu` | 底层 GPU 驱动抽象 |
| `GrDirectContext` | GPU 上下文 |
| `skgpu::UniqueKey` | 唯一键实现 |
| `skgpu::ScratchKey` | 临时键实现 |
| `SkTraceMemoryDump` | 内存追踪接口 |
| `GrTypesPriv.h` | Ganesh 内部类型定义 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `GrGpuBuffer` | 继承 `GrGpuResource` 实现缓冲区资源 |
| `GrTexture` | 继承 `GrGpuResource` 实现纹理资源 |
| `GrRenderTarget` | 继承 `GrGpuResource` 实现渲染目标 |
| `GrAttachment` | 继承 `GrGpuResource` 实现附件资源 |
| `GrSurfaceProxy` | 通过 `ProxyAccess` 管理资源引用 |
| `GrResourceCache` | 通过 `CacheAccess` 管理资源生命周期 |

## 设计模式与设计决策

### 设计模式

1. **CRTP (Curiously Recurring Template Pattern)**
   - `GrIORef<GrGpuResource>` 使用 CRTP 实现静态多态
   - 避免虚函数调用开销
   - 在编译期绑定 `notifyARefCntIsZero()`

2. **特权访问器模式 (Privileged Accessor)**
   - `CacheAccess`, `ResourcePriv`, `ProxyAccess` 提供分级访问控制
   - 避免暴露内部接口给公共 API
   - 通过友元关系精确控制访问权限

3. **模板方法模式 (Template Method)**
   - `onRelease()`, `onAbandon()`, `onGpuMemorySize()` 定义扩展点
   - 基类控制调用时机和流程
   - 子类实现具体行为

4. **策略模式 (Strategy Pattern)**
   - `GrBudgetedType` 定义不同的预算策略
   - `computeScratchKey()` 允许子类定义复用策略

5. **观察者模式 (Observer)**
   - 引用计数归零时通知 `GrResourceCache`
   - 预算状态改变时通知缓存

### 关键设计决策

1. **为何需要双重引用计数?**
   - 主引用计数表示逻辑所有权
   - 命令缓冲区计数防止提前释放
   - 两者都归零才能真正删除资源

2. **Scratch Key 与 Unique Key 的分离**
   - Scratch Key: 支持资源复用,减少分配开销
   - Unique Key: 实现去重,避免重复创建相同资源
   - 一个资源可以从 Scratch 转为 Unique,但不能反向

3. **包装资源的特殊处理**
   - `fRefsWrappedObjects` 标记外部资源
   - 永远不可预算(不占用缓存预算)
   - 可缓存(支持 Unique Key)或不可缓存
   - Unique Key 提供弱引用语义

4. **延迟 GPU 内存计算**
   - 首次调用 `gpuMemorySize()` 时才计算
   - 缓存计算结果避免重复开销
   - 使用 `kInvalidGpuMemorySize` 标记未计算状态

5. **时间戳与可清除时间**
   - `fTimestamp`: LRU 缓存策略的排序依据
   - `fTimeWhenBecamePurgeable`: 支持基于时间的清理策略
   - 允许实现"最近未使用超过 N 秒"的清理规则

6. **零引用到一引用的特权转换**
   - `ProxyAccess::ref()` 允许代理复活零引用资源
   - 支持延迟资源实例化
   - 必须通过缓存确保资源仍然有效

## 性能考量

### 原子操作优化

1. **内存序优化**
   - `ref()` 使用 `memory_order_relaxed`: 最小开销
   - `unref()` 使用 `memory_order_acq_rel`: 确保释放安全
   - 避免不必要的内存屏障

2. **缓存友好设计**
   - 常用字段 (`fGpu`, `fGpuMemorySize`) 放在前面
   - 减少缓存行跨越

### 缓存策略优化

1. **Scratch Key 复用**
   - 避免重复创建相同大小的缓冲区/纹理
   - 减少 GPU 驱动调用
   - 特别适用于临时资源

2. **Unique Key 去重**
   - 避免重复创建相同内容的资源
   - 减少内存占用
   - 加速资源查找

3. **LRU 清理策略**
   - 通过时间戳快速识别最少使用的资源
   - 支持基于时间的老化策略
   - 平衡内存占用和性能

### 延迟计算

- GPU 内存大小延迟计算
- Scratch Key 仅在需要时计算
- 减少构造函数开销

### 调试开销隔离

- 内存追踪仅在需要时启用
- 调试字段使用条件编译
- Release 版本无额外开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrResourceCache.h` | 协作 | 资源缓存管理器 |
| `src/gpu/ganesh/GrGpuResourceCacheAccess.h` | 定义 | CacheAccess 接口定义 |
| `src/gpu/ganesh/GrGpuResourcePriv.h` | 定义 | ResourcePriv 接口定义 |
| `src/gpu/ganesh/GrGpu.h` | 依赖 | GPU 驱动抽象层 |
| `src/gpu/ganesh/GrGpuBuffer.h` | 继承 | 缓冲区资源实现 |
| `src/gpu/ganesh/GrTexture.h` | 继承 | 纹理资源实现 |
| `src/gpu/ganesh/GrRenderTarget.h` | 继承 | 渲染目标实现 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 使用 | Surface 代理类 |
| `src/gpu/ResourceKey.h` | 依赖 | 键值系统实现 |
| `include/gpu/ganesh/GrDirectContext.h` | 依赖 | DirectContext 定义 |
