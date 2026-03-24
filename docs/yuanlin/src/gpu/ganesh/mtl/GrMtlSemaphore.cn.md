# GrMtlSemaphore

> 源文件
> - `src/gpu/ganesh/mtl/GrMtlSemaphore.h`
> - `src/gpu/ganesh/mtl/GrMtlSemaphore.mm`

## 概述

`GrMtlSemaphore` 是 Ganesh 图形后端中 Metal 实现的信号量类,用于在 GPU 命令队列之间或 GPU 与 CPU 之间进行同步。该类基于 Metal 的 `MTLEvent` 对象实现,支持细粒度的命令依赖管理和执行顺序控制。通过封装 Metal 事件和关联的值,提供了跨平台的信号量语义,用于协调渲染操作的执行时序,确保数据依赖的正确性。

## 架构位置

`GrMtlSemaphore` 位于 Skia 图形库的 GPU 后端同步原语层次结构中:

```
Skia 图形库
└── GPU 后端 (src/gpu)
    └── Ganesh 渲染引擎 (ganesh)
        ├── GrSemaphore (信号量抽象基类)
        │   └── GrMtlSemaphore (Metal 信号量) ← 当前类
        ├── GrManagedResource (资源管理基类)
        │   └── GrMtlEvent (Metal 事件封装) ← 辅助类
        └── Metal 后端实现 (mtl)
            ├── GrMtlGpu (GPU 接口)
            └── GrMtlCommandBuffer (命令缓冲)
```

该类为 Metal 后端提供同步机制,与命令缓冲和 GPU 接口协作实现命令依赖管理。

## 主要类与结构体

### GrMtlEvent 类

封装 Metal 事件对象的资源管理类。

**继承关系:**
- 继承: `GrManagedResource` (托管资源基类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMtlEvent` | `mutable id<MTLEvent>` | Metal 事件对象,标记为 `mutable` 支持延迟释放 |

**主要方法:**

```cpp
static sk_sp<GrMtlEvent> Make(GrMtlGpu* gpu)
```
从 GPU 设备创建新的 Metal 事件。

```cpp
static sk_sp<GrMtlEvent> MakeWrapped(GrMTLHandle event)
```
包装外部 Metal 事件,接管所有权。

```cpp
id<MTLEvent> mtlEvent() const
```
返回底层 Metal 事件对象。

### GrMtlSemaphore 类

Metal 信号量实现类。

**继承关系:**
- 继承: `GrSemaphore` (信号量抽象基类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fEvent` | `sk_sp<GrMtlEvent>` | 底层 Metal 事件对象 |
| `fValue` | `uint64_t` | 信号量值,用于标识事件状态 |

## 公共 API 函数

### 工厂方法

```cpp
static std::unique_ptr<GrMtlSemaphore> Make(GrMtlGpu* gpu)
```
创建新的 Metal 信号量,初始值为 1。如果平台不支持 `MTLEvent`(macOS < 10.14),返回 `nullptr`。

```cpp
static std::unique_ptr<GrMtlSemaphore> MakeWrapped(
    GrMTLHandle mtlEvent,
    uint64_t value)
```
包装外部 Metal 事件,创建指定值的信号量。用于与外部代码互操作。

### 访问器

```cpp
sk_sp<GrMtlEvent> event()
```
返回底层事件对象的智能指针。

```cpp
uint64_t value() const
```
返回当前信号量值。

```cpp
GrBackendSemaphore backendSemaphore() const override
```
转换为跨平台的后端信号量表示,用于与其他 API 互操作。

## 内部实现细节

### Metal 事件机制

Metal 事件基于时间线信号量模型:

1. **事件对象**: `id<MTLEvent>` 是 Metal 的同步原语
2. **事件值**: 64 位无符号整数,标识事件的特定状态
3. **等待语义**: 命令可以等待事件达到或超过指定值
4. **信号语义**: 命令完成时将事件设置为指定值

### 平台可用性检查

所有 Metal 事件操作都包含运行时版本检查:

```objc
if (@available(macOS 10.14, iOS 12.0, tvOS 12.0, *)) {
    // Metal 事件操作
}
```

这确保在不支持 Metal 事件的旧平台上优雅降级。

### 所有权管理

`MakeWrapped()` 使用 `__bridge_transfer` 转移所有权:

```objc
id<MTLEvent> mtlEvent = (__bridge_transfer id<MTLEvent>)event;
```

这将 `GrMTLHandle`(C 风格指针)转换为 ARC 管理的 Objective-C 对象,避免内存泄漏。

### 后端信号量转换

`backendSemaphore()` 使用 `__bridge_retained` 增加引用计数:

```objc
GrMTLHandle handle = (__bridge_retained GrMTLHandle)(fEvent->mtlEvent());
```

调用者负责后续释放,支持跨 API 边界传递。

### 资源释放

`GrMtlEvent::freeGPUData()` 实现延迟释放:

```cpp
void freeGPUData() const override {
    if (@available(...)) {
        fMtlEvent = nil;
    }
}
```

标记为 `const` 但修改 `mutable` 成员,支持在 `const` 上下文中释放资源。

### 初始值设计

新创建的信号量初始值为 1:

```cpp
new GrMtlSemaphore(std::move(event), 1)
```

值 0 通常保留给未信号状态,值 1 表示初始可用状态。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrSemaphore` | 信号量抽象基类 |
| `GrManagedResource` | 资源管理基类 |
| `GrMtlGpu` | Metal GPU 接口,提供设备访问 |
| `GrBackendSemaphore` | 跨平台信号量表示 |
| `GrMtlUtil` | Metal 工具函数和类型定义 |
| `Metal.framework` | Metal API |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `GrMtlCommandBuffer` | 使用信号量进行命令同步 |
| `GrMtlGpu` | 创建和管理信号量 |
| `GrContext` | 跨上下文同步 |

## 设计模式与设计决策

### 1. 桥接模式 (Bridge Pattern)

`GrMtlSemaphore` 作为平台无关接口 `GrSemaphore` 的具体实现,将抽象与实现分离:

```cpp
GrSemaphore (抽象)
    ↓
GrMtlSemaphore (Metal 实现)
    ↓
MTLEvent (平台 API)
```

### 2. 适配器模式 (Adapter Pattern)

`backendSemaphore()` 将 Metal 特定的信号量适配为跨平台的 `GrBackendSemaphore`:

```cpp
GrBackendSemaphore backendSemaphore() const override;
```

### 3. 工厂模式 (Factory Pattern)

静态工厂方法封装复杂的创建逻辑,包括平台检查和所有权管理:

```cpp
static std::unique_ptr<GrMtlSemaphore> Make(GrMtlGpu* gpu);
static std::unique_ptr<GrMtlSemaphore> MakeWrapped(...);
```

### 4. RAII 资源管理

使用智能指针自动管理资源生命周期:

```cpp
sk_sp<GrMtlEvent> fEvent;  // 自动引用计数
```

### 5. 分离关注点

将 Metal 事件封装在 `GrMtlEvent` 中,与信号量语义(`GrMtlSemaphore`)分离:
- `GrMtlEvent`: 管理 Metal API 对象
- `GrMtlSemaphore`: 实现信号量语义(事件 + 值)

### 6. 惰性平台检查

运行时检查平台版本而非编译时,支持在不同平台上编译相同代码:

```objc
@available(macOS 10.14, iOS 12.0, tvOS 12.0, *)
```

## 性能考量

### 1. 轻量级同步

Metal 事件是硬件级同步原语,比 CPU 屏障更高效:
- GPU 直接处理等待和信号
- 不需要 CPU 干预
- 支持细粒度依赖管理

### 2. 零拷贝设计

信号量仅存储事件指针和值,总大小仅 16 字节(64 位平台):

```cpp
sk_sp<GrMtlEvent> fEvent;  // 8 字节
uint64_t fValue;           // 8 字节
```

### 3. 智能指针开销

使用 `sk_sp` 和 `std::unique_ptr` 引入引用计数开销,但提供自动内存管理:
- 引用计数原子操作
- 智能指针复制成本

### 4. 平台检查成本

每次访问 Metal 事件都需要运行时版本检查,但编译器优化可以消除重复检查。

### 5. 桥接开销

Objective-C 桥接操作(`__bridge`, `__bridge_retained`, `__bridge_transfer`)引入少量开销,但对于低频同步操作可接受。

### 6. 调试支持

`dumpInfo()` 提供资源跟踪,仅在 `SK_TRACE_MANAGED_RESOURCES` 定义时编译,生产环境无开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrSemaphore.h` | 继承关系 | 信号量抽象基类 |
| `src/gpu/ganesh/GrManagedResource.h` | 继承关系 | 资源管理基类 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` | 使用关系 | GPU 接口,创建信号量 |
| `src/gpu/ganesh/mtl/GrMtlCommandBuffer.h/mm` | 使用关系 | 命令缓冲使用信号量 |
| `src/gpu/ganesh/mtl/GrMtlUtil.h` | 使用关系 | Metal 工具和类型定义 |
| `include/gpu/ganesh/GrBackendSemaphore.h` | 使用关系 | 跨平台信号量表示 |
| `include/gpu/ganesh/mtl/GrMtlBackendSemaphore.h` | 使用关系 | Metal 后端信号量工具 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 使用关系 | 内部类型定义 |
