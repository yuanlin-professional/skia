# GrManagedResource

> 源文件: src/gpu/ganesh/GrManagedResource.h, src/gpu/ganesh/GrManagedResource.cpp

## 概述

`GrManagedResource` 是 Skia Ganesh GPU 后端中用于管理 GPU 资源的基础类。它实现了一套引用计数机制,专门用于管理可能被多个对象共享的 GPU 资源,特别是在命令缓冲区追踪的对象中。该类与 `SkRefCntBase` 非常相似,但针对 GPU 资源的生命周期管理进行了特殊设计。

该模块提供了三个核心类:
- `GrManagedResource`: 基础资源管理类,提供引用计数和 GPU 数据释放机制
- `GrRecycledResource`: 支持资源回收的子类
- `GrTextureResource`: 专门用于纹理资源管理的子类,实现了释放回调机制

## 架构位置

`GrManagedResource` 位于 Skia 的 GPU 渲染后端 Ganesh 的核心资源管理层。它处于资源管理体系的底层,为更高级的 GPU 资源类提供基础的生命周期管理能力。该类主要在以下场景中使用:

1. 作为 Vulkan/Metal 等后端特定资源的基类
2. 在命令缓冲区中追踪资源依赖关系
3. 管理需要在多个渲染操作间共享的 GPU 对象

在 Ganesh 架构中,它与 `GrGpuResource` 形成互补关系:`GrGpuResource` 用于可缓存的资源,而 `GrManagedResource` 用于不参与缓存但需要引用计数管理的资源。

## 主要类与结构体

### GrManagedResource 继承关系

```
SkNoncopyable
    └── GrManagedResource
            ├── GrRecycledResource
            └── GrTextureResource
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRefCnt` | `std::atomic<int32_t>` | 原子引用计数器,初始值为 1 |
| `fKey` | `uint32_t` | 调试模式下的唯一标识符 |
| `fKeyCounter` | `static std::atomic<uint32_t>` | 全局计数器,用于生成唯一 key |

### GrRecycledResource 成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| 无额外成员 | - | 仅添加了 `recycle()` 行为 |

### GrTextureResource 成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fReleaseHelper` | `sk_sp<GrSurface::RefCntedReleaseProc>` | 释放回调辅助对象 |

## 公共 API 函数

### GrManagedResource 核心接口

```cpp
// 构造函数 - 初始化引用计数为 1
GrManagedResource();

// 析构函数 - 断言引用计数必须为 1
virtual ~GrManagedResource();

// 增加引用计数
void ref() const;

// 减少引用计数,当计数归零时释放 GPU 数据并删除对象
void unref() const;

// 检查是否只有一个引用持有者
bool unique() const;

// 调试接口 - 获取当前引用计数
int32_t getRefCnt() const;  // 仅 SK_DEBUG

// 调试接口 - 验证引用计数状态
void validate() const;  // 仅 SK_DEBUG

// 调试接口 - 输出资源信息
virtual void dumpInfo() const = 0;  // 仅 SK_TRACE_MANAGED_RESOURCES
```

### GrRecycledResource 接口

```cpp
// 回收或释放资源
// 如果只有一个引用,调用 onRecycle()
// 否则调用 unref()
void recycle() const;

// 子类必须实现的回收处理
virtual void onRecycle() const = 0;
```

### GrTextureResource 接口

```cpp
// 设置纹理释放时的回调
void setRelease(sk_sp<GrSurface::RefCntedReleaseProc> releaseHelper);

// 触发释放回调
void invokeReleaseProc() const;
```

## 内部实现细节

### 引用计数机制

`GrManagedResource` 采用了原子操作实现线程安全的引用计数:

1. **ref() 实现**: 使用 `memory_order_relaxed` 增加计数,因为增加引用不需要内存同步
2. **unref() 实现**: 使用 `memory_order_acq_rel` 减少计数,确保所有之前的操作都完成
3. **unique() 实现**: 使用 `memory_order_acquire` 检查唯一性,防止条件代码提前执行

### 资源释放流程

当引用计数归零时,`internal_dispose()` 执行以下步骤:
1. 调用纯虚函数 `freeGPUData()` 释放 GPU 资源
2. 在追踪模式下从全局追踪表中移除
3. 在调试模式下临时恢复引用计数为 1 以满足析构函数断言
4. 调用 delete 删除对象

### 调试追踪系统

在 `SK_TRACE_MANAGED_RESOURCES` 定义时,系统维护一个全局哈希集合追踪所有活跃的资源:
- 每个资源创建时分配唯一的 key
- 资源添加到全局 `Trace` 对象的哈希集合中
- 析构时从集合中移除
- 程序结束时检测泄漏

### 纹理资源释放回调

`GrTextureResource` 通过 `RefCntedReleaseProc` 实现延迟释放:
- `fReleaseHelper` 持有回调的智能指针
- 当智能指针引用计数归零时,自动触发回调
- 支持在纹理不再使用时执行清理操作(如解锁 SkImage)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkRefCnt.h` | 参考引用计数设计 |
| `SkNoncopyable` | 基类,禁止拷贝 |
| `SkMutex` | 调试追踪的线程同步 |
| `SkTHash.h` | 追踪系统的哈希集合 |
| `GrSurface.h` | 纹理释放回调类型定义 |
| `<atomic>` | 原子引用计数实现 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| Vulkan 后端资源类 | 继承 `GrManagedResource` 管理 Vulkan 对象 |
| Metal 后端资源类 | 继承 `GrManagedResource` 管理 Metal 对象 |
| 命令缓冲区 | 使用 `ref()/unref()` 追踪资源生命周期 |
| 纹理代理 | 通过 `GrTextureResource` 管理纹理释放 |

## 设计模式与设计决策

### 设计模式

1. **引用计数模式 (Reference Counting)**
   - 自动化资源生命周期管理
   - 避免显式的所有权转移

2. **模板方法模式 (Template Method)**
   - `freeGPUData()` 作为纯虚函数,由子类实现具体释放逻辑
   - `onRecycle()` 定义回收框架,子类实现具体策略

3. **策略模式 (Strategy Pattern)**
   - `GrRecycledResource` 定义资源回收策略
   - 允许子类决定是回收还是释放

4. **CRTP 式的单例追踪**
   - `Trace::GetTrace()` 返回静态单例用于全局资源追踪

### 关键设计决策

1. **为何不使用 SkRefCnt?**
   - 需要在 `unref()` 时执行特定的 GPU 清理逻辑
   - 需要与命令缓冲区系统集成
   - 提供更精细的内存屏障控制

2. **初始引用计数为 1**
   - 遵循"创建者拥有"原则
   - 析构时要求计数为 1,防止误用

3. **const 成员函数的 ref/unref**
   - 允许 const 对象修改引用计数
   - 使用 mutable atomic 实现
   - 符合引用计数语义(逻辑 const)

4. **回收与释放分离**
   - `GrRecycledResource` 提供资源复用机制
   - 减少 GPU 对象创建开销
   - 支持对象池模式

5. **调试支持的权衡**
   - 仅在 Debug 模式启用完整追踪
   - 使用条件编译减少 Release 版本开销
   - 提供 `dumpInfo()` 帮助定位泄漏

## 性能考量

### 原子操作优化

1. **内存序选择**
   - `ref()` 使用 `relaxed`: 最小开销,无同步需求
   - `unref()` 使用 `acq_rel`: 确保释放前所有操作完成
   - `unique()` 使用 `acquire`: 仅在返回 true 时需要同步

2. **缓存行效应**
   - `fRefCnt` 作为第一个成员变量,减少缓存未命中
   - 独立的缓存行避免伪共享

### 资源释放优化

1. **延迟释放**
   - 通过 `RefCntedReleaseProc` 实现异步清理
   - 避免在渲染关键路径上执行耗时操作

2. **回收机制**
   - `GrRecycledResource` 避免频繁的 GPU 对象创建/销毁
   - 适用于帧间重复使用的临时缓冲区

### 调试开销隔离

- 追踪系统仅在 `SK_TRACE_MANAGED_RESOURCES` 时启用
- 使用 `SkDEBUGCODE` 宏确保 Release 版本零开销
- `fKey` 字段仅在追踪模式存在

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuResource.h` | 互补 | 可缓存的 GPU 资源基类 |
| `src/gpu/ganesh/GrSurface.h` | 依赖 | 定义释放回调类型 |
| `src/gpu/ganesh/vk/GrVkImage.h` | 继承 | Vulkan 图像资源实现 |
| `src/gpu/ganesh/mtl/GrMtlTexture.h` | 继承 | Metal 纹理资源实现 |
| `src/gpu/ganesh/GrCommandBuffer.h` | 使用 | 命令缓冲区追踪资源依赖 |
| `include/core/SkRefCnt.h` | 参考 | Skia 标准引用计数实现 |
| `src/core/SkTHash.h` | 使用 | 调试追踪哈希表 |
