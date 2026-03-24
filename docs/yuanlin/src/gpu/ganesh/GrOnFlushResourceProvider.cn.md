# GrOnFlushResourceProvider

> 源文件
> - src/gpu/ganesh/GrOnFlushResourceProvider.h
> - src/gpu/ganesh/GrOnFlushResourceProvider.cpp

## 概述

`GrOnFlushResourceProvider` 是 Ganesh GPU 后端中用于在刷新（flush）操作期间提供资源访问的轻量级包装类。它与 `GrOnFlushCallbackObject` 配合使用，允许子系统（如文本渲染、路径渲染器）在特定刷新操作期间创建和管理 GPU 资源，特别是图集（atlases）。该类限制了回调函数可以访问的 `GrDrawingManager` 功能，提供了一个受控的接口来处理刷新时的资源实例化。

## 架构位置

`GrOnFlushResourceProvider` 位于 Skia GPU 渲染管线的刷新阶段，作为 `GrDrawingManager` 的浅层封装。它在 Ganesh 架构中处于中间层，介于高级绘图管理和底层 GPU 资源管理之间。当执行刷新操作时，它被传递给已注册的 `GrOnFlushCallbackObject` 实例，为这些回调提供有限但必要的资源访问能力。

```
GrDirectContext
    └── GrDrawingManager
        └── GrOnFlushResourceProvider (包装层)
            └── 传递给 GrOnFlushCallbackObject::preFlush/postFlush
```

## 主要类与结构体

### GrOnFlushCallbackObject

这是所有预刷新回调对象必须派生的基类。

**继承关系**
- 基类：无（纯虚基类）
- 子类：各种子系统的回调实现（如文本渲染器、路径渲染器等）

**关键方法**

| 方法名 | 返回类型 | 说明 |
|--------|----------|------|
| `preFlush` | `bool` | 在刷新前调用，允许创建图集等资源，返回是否成功 |
| `postFlush` | `void` | 在刷新完成后调用，用于追踪资源使用情况 |
| `retainOnFreeGpuResources` | `bool` | 指示在释放 GPU 资源时是否保留此回调对象 |

### GrOnFlushResourceProvider

轻量级的资源提供者包装类。

**继承关系**
- 无继承关系，纯包装类

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fDrawingMgr` | `GrDrawingManager*` | 指向绘图管理器的指针 |

## 公共 API 函数

### GrOnFlushResourceProvider 类

| 函数签名 | 说明 |
|----------|------|
| `explicit GrOnFlushResourceProvider(GrDrawingManager*)` | 构造函数，接收绘图管理器指针 |
| `bool instantiateProxy(GrSurfaceProxy*)` | 实例化表面代理对象，返回是否成功 |
| `const GrCaps* caps() const` | 获取 GPU 能力信息 |
| `bool failFlushTimeCallbacks() const` | （测试用）检查是否故意失败刷新回调 |

### GrOnFlushCallbackObject 类

| 函数签名 | 说明 |
|----------|------|
| `virtual bool preFlush(GrOnFlushResourceProvider*)` | 刷新前回调，用于创建资源 |
| `virtual void postFlush(skgpu::Token)` | 刷新后回调，用于追踪资源 |
| `virtual bool retainOnFreeGpuResources()` | 是否在释放资源时保留回调对象 |

## 内部实现细节

### 代理实例化逻辑

`instantiateProxy` 方法的实现包含以下关键步骤：

1. **验证代理状态**：首先断言代理可以跳过资源分配器（`canSkipResourceAllocator()`）
2. **获取直接上下文**：通过 `fDrawingMgr` 获取 `GrDirectContext`，如果无法获取则返回失败
3. **获取资源提供者**：从直接上下文获取 `GrResourceProvider`
4. **处理延迟实例化**：如果代理是延迟（lazy）类型，调用 `doLazyInstantiation`
5. **标准实例化**：否则调用标准的 `instantiate` 方法

```cpp
bool GrOnFlushResourceProvider::instantiateProxy(GrSurfaceProxy* proxy) {
    SkASSERT(proxy->canSkipResourceAllocator());

    auto direct = fDrawingMgr->getContext()->asDirectContext();
    if (!direct) {
        return false;
    }

    auto resourceProvider = direct->priv().resourceProvider();

    if (proxy->isLazy()) {
        return proxy->priv().doLazyInstantiation(resourceProvider);
    }

    return proxy->instantiate(resourceProvider);
}
```

### 能力查询

`caps()` 方法提供对 GPU 能力的只读访问，通过绘图管理器的上下文获取：

```cpp
const GrCaps* GrOnFlushResourceProvider::caps() const {
    return fDrawingMgr->getContext()->priv().caps();
}
```

### 测试支持

在 GPU_TEST_UTILS 宏定义时，提供 `failFlushTimeCallbacks()` 方法用于测试刷新回调失败的场景。

## 依赖关系

### 依赖的模块

| 模块名 | 用途 |
|--------|------|
| `GrDrawingManager` | 提供绘图管理功能和上下文访问 |
| `GrDirectContext` | GPU 上下文管理 |
| `GrRecordingContext` | 记录绘图操作的上下文 |
| `GrSurfaceProxy` | 表面代理对象，延迟资源分配 |
| `GrCaps` | GPU 能力查询 |
| `skgpu::Token` | 令牌跟踪系统，用于资源同步 |

### 被依赖的模块

| 模块名 | 使用方式 |
|--------|----------|
| 文本渲染器 | 在刷新时创建文本图集 |
| 路径渲染器 | 在刷新时创建路径图集 |
| 其他图集管理器 | 在刷新时创建和更新各类图集 |
| `GrDrawingManager` | 注册和调用刷新回调 |

## 设计模式与设计决策

### 包装器模式（Wrapper Pattern）

`GrOnFlushResourceProvider` 采用包装器模式，封装了 `GrDrawingManager` 的功能，只暴露刷新回调所需的最小接口。这种设计有几个优点：

1. **最小权限原则**：限制回调对绘图管理器的访问，防止误用
2. **接口稳定性**：即使 `GrDrawingManager` 内部变化，包装接口可以保持稳定
3. **安全性**：防止回调执行不安全的操作

### 回调机制

采用虚函数接口 `GrOnFlushCallbackObject` 实现回调机制，允许不同子系统在刷新时执行特定操作：

- **preFlush**：在刷新前准备资源，如创建图集
- **postFlush**：在刷新后清理或更新状态

### 无虚函数设计

`GrOnFlushResourceProvider` 本身没有虚函数，这是有意为之的设计决策：

- 避免额外的虚函数表开销
- 确保对象大小保持最小
- 强调其作为轻量级包装的角色

注释明确指出："It should never have additional data members or virtual methods."

### 禁止拷贝

通过删除拷贝构造函数和赋值操作符，防止对象被复制，确保每个 provider 实例的唯一性和生命周期控制。

## 性能考量

### 轻量级设计

该类设计为极其轻量：
- 仅包含一个指针成员
- 无虚函数表
- 无动态内存分配

### 内联构造

构造函数在头文件中内联定义，避免函数调用开销：

```cpp
explicit GrOnFlushResourceProvider(GrDrawingManager* drawingMgr)
    : fDrawingMgr(drawingMgr) {}
```

### 延迟资源分配

通过 `instantiateProxy` 支持延迟实例化，允许在真正需要时才分配 GPU 资源，优化内存使用。

### 同步开销

刷新回调在 GPU 管线的关键路径上执行，因此需要高效完成。该类提供的接口设计为最小化同步和查询开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrDrawingManager.h/cpp` | 核心依赖 | 管理绘图操作和刷新流程 |
| `src/gpu/ganesh/GrDirectContext.h` | 上下文 | GPU 直接上下文 |
| `src/gpu/ganesh/GrSurfaceProxy.h/cpp` | 资源管理 | 表面代理实例化 |
| `src/gpu/ganesh/GrCaps.h` | 能力查询 | GPU 能力信息 |
| `src/gpu/ganesh/GrAtlasTypes.h` | 类型定义 | 图集相关类型 |
| `include/gpu/ganesh/GrContextOptions.h` | 配置 | 上下文选项（测试配置） |
