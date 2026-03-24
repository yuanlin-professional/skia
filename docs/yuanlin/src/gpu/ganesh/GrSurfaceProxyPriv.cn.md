# GrSurfaceProxyPriv

> 源文件: src/gpu/ganesh/GrSurfaceProxyPriv.h

## 概述

`GrSurfaceProxyPriv` 是一个特权访问类（privileged access class），为 `GrSurfaceProxy` 提供仅供 Skia 内部使用的私有 API。这是一种常见的 C++ 设计模式，通过友元类机制提供受控的私有成员访问，避免将内部方法暴露为公共 API。

该类本身不包含任何数据成员或虚函数，纯粹作为访问 `GrSurfaceProxy` 私有和受保护成员的"窗口"。这种设计使得内部操作接口与公共接口明确分离，提高了代码的可维护性和安全性。

## 架构位置

`GrSurfaceProxyPriv` 位于 Ganesh GPU 后端的内部 API 层：

- **服务对象**: `GrSurfaceProxy` 及其子类
- **调用者**: `GrResourceAllocator`、`GrRenderTask`、资源管理内部代码
- **访问模式**: 通过 `GrSurfaceProxy::priv()` 方法获取
- **设计目的**: 隔离内部 API 和公共 API
- **类似类**: Skia 中许多类都有对应的 `*Priv` 类（如 `SkCanvasPriv`、`GrContextPriv`）

这种模式在 Skia 代码库中广泛使用，是实现 API 层次分离的标准方式。

## 主要类与结构体

### GrSurfaceProxyPriv 类

**继承关系:** 无继承，独立的工具类

**关键特点:**
- 纯访问器类，无数据成员
- 无虚函数
- 禁止获取地址（防止误用）
- 只能通过 `GrSurfaceProxy::priv()` 创建

**成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fProxy` | `GrSurfaceProxy*` | 指向被访问的 proxy 对象 |

## 公共 API 函数

### Scratch Key 操作

```cpp
void computeScratchKey(const GrCaps& caps, skgpu::ScratchKey* key) const
```

计算 scratch key，用于资源复用：
- 委托给 `fProxy->computeScratchKey()`
- 需要传入 `GrCaps` 以获取 GPU 能力信息
- Scratch key 用于在资源池中查找可复用的资源

### Surface 创建

```cpp
sk_sp<GrSurface> createSurface(GrResourceProvider* resourceProvider) const
```

直接创建 GPU surface：
- 调用 `fProxy->createSurface()`（纯虚函数，由子类实现）
- 返回创建的 surface 智能指针
- 用于强制实例化或测试场景

### Surface 分配

```cpp
void assign(sk_sp<GrSurface> surface)
```

将已创建的 surface 分配给 proxy：
- 调用 `fProxy->assign()`
- 用于延迟实例化或包装现有 surface
- 只能在 proxy 未实例化时调用

### Backing Fit 查询和修改

```cpp
bool isExact() const
```

检查是否精确匹配：
- 返回 `SkBackingFit::kExact == fProxy->fFit`
- 直接访问私有成员 `fFit`

```cpp
void exactify()
```

强制将 proxy 转换为精确匹配模式：
- 将 `kApprox` 变为 `kExact`
- 更新尺寸为实际后备存储尺寸
- **警告**: 注释中明确提示"Don't. Just don't."（不要使用）
- 仅在特殊情况下使用（如 `SkSpecialImage`）

### Lazy Proxy 操作

```cpp
void setLazyDimensions(SkISize dimensions)
```

设置延迟 proxy 的尺寸：
- 调用 `fProxy->setLazyDimensions()`
- 用于 fully lazy proxy 在实例化前确定尺寸

```cpp
bool doLazyInstantiation(GrResourceProvider*)
```

执行延迟实例化：
- 调用延迟回调函数创建 surface
- 处理 unique key 同步
- 返回是否成功

### DDL 和 Promise 标记

```cpp
void setIsDDLTarget()
```

标记为 DDL（Deferred Display List）目标：
- 设置 `fProxy->fIsDDLTarget = true`
- 用于跨线程渲染场景

```cpp
void setIsPromiseProxy()
```

标记为 promise proxy：
- 设置 `fProxy->fIsPromiseProxy = true`
- 用于延迟纹理加载

## 内部实现细节

### 构造和访问控制

```cpp
explicit GrSurfaceProxyPriv(GrSurfaceProxy* proxy) : fProxy(proxy) {}
```

- **私有构造函数**: 只能通过 `GrSurfaceProxy::priv()` 创建
- **友元关系**: 声明 `GrSurfaceProxy` 为友元

```cpp
const GrSurfaceProxyPriv* operator&() const;
GrSurfaceProxyPriv* operator&();
```

- **禁止取地址**: 防止存储或传递指针
- **强制临时使用**: 只能作为临时对象使用

### priv() 方法实现

在 `GrSurfaceProxy` 中：
```cpp
inline GrSurfaceProxyPriv GrSurfaceProxy::priv() {
    return GrSurfaceProxyPriv(this);
}

inline const GrSurfaceProxyPriv GrSurfaceProxy::priv() const {
    return GrSurfaceProxyPriv(const_cast<GrSurfaceProxy*>(this));
}
```

- **按值返回**: 创建临时对象
- **const 重载**: 支持 const 和非 const 访问
- **const_cast**: const 版本需要移除 const（因为 priv 类持有非 const 指针）

### exactify() 实现

在 `GrSurfaceProxy.cpp` 中实现：
```cpp
void GrSurfaceProxyPriv::exactify() {
    SkASSERT(!fProxy->isFullyLazy());
    if (this->isExact()) {
        return;  // 已经是精确的
    }
    SkASSERT(SkBackingFit::kApprox == fProxy->fFit);
    fProxy->fDimensions = fProxy->fTarget ? fProxy->fTarget->dimensions()
                                          : fProxy->backingStoreDimensions();
    fProxy->fFit = SkBackingFit::kExact;
}
```

关键逻辑：
1. 检查不是 fully lazy
2. 如果已是精确的，直接返回
3. 更新尺寸为实际尺寸
4. 设置 fit 为 kExact

### doLazyInstantiation() 实现

复杂的延迟实例化逻辑：
1. 尝试从缓存中查找（如果有 unique key）
2. 调用 `fLazyInstantiateCallback` 创建 surface
3. 处理 fully lazy proxy 的尺寸确定
4. 同步 unique key（如果需要）
5. 分配 surface 给 proxy
6. 根据配置释放回调函数

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrSurfaceProxy` | 被访问的目标类 |
| `GrSurface` | 创建和分配的资源 |
| `GrResourceProvider` | 资源创建 |
| `GrCaps` | GPU 能力查询 |
| `skgpu::ScratchKey` | Scratch key 类型 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrResourceAllocator` | 资源分配调度，调用 `doLazyInstantiation()` |
| `GrRenderTask` | 任务执行，访问私有方法 |
| `GrProxyProvider` | Proxy 创建和管理 |
| `SkSpecialImage` | 调用 `exactify()`（虽然不推荐） |
| 各种 GPU 测试代码 | 使用 `createSurface()` 等方法 |

## 设计模式与设计决策

### Privileged Access 模式

这是一种常见的 C++ 模式，用于提供受控的私有访问：

**优势:**
1. **接口分离**: 公共 API 和内部 API 明确分离
2. **类型安全**: 编译时检查访问权限
3. **文档清晰**: 内部方法集中在 `*Priv` 类中
4. **代码组织**: 避免 `GrSurfaceProxy` 公共接口过于庞大

**实现要点:**
- `*Priv` 类无数据成员
- 通过友元关系访问私有成员
- 按值返回，作为临时对象使用
- 禁止取地址

### 为什么不用友元函数

相比直接使用友元函数，`*Priv` 类的优势：
- **命名空间隔离**: `priv().method()` 清晰表明是内部 API
- **集中管理**: 所有内部方法集中在一个类中
- **易于查找**: 搜索 `Priv` 即可找到所有内部 API
- **代码组织**: 相关方法分组

### const 正确性的权衡

```cpp
inline const GrSurfaceProxyPriv GrSurfaceProxy::priv() const {
    return GrSurfaceProxyPriv(const_cast<GrSurfaceProxy*>(this));
}
```

使用 `const_cast` 移除 const：
- **原因**: `*Priv` 类的某些方法需要修改 proxy
- **安全性**: 调用者负责确保不在 const 对象上调用修改方法
- **实用性**: 避免维护两套 `*Priv` 类（const 和非 const）

### 禁止取地址的原因

```cpp
const GrSurfaceProxyPriv* operator&() const;  // 未定义
GrSurfaceProxyPriv* operator&();              // 未定义
```

**防止误用:**
- 不能存储 `*Priv` 对象的指针
- 强制作为临时对象使用
- 避免生命周期问题（`*Priv` 只是一个"窗口"）

### exactify() 的"警告"设计

注释中写道："Don't. Just don't."（不要使用）

**原因:**
- 改变 proxy 的语义（从近似变精确）
- 可能导致资源分配器的假设失效
- 只在极特殊场景下需要（如 `SkSpecialImage` 的安全区域优化）

**保留的原因:**
- 某些遗留代码需要
- 明确的警告提醒开发者

## 性能考量

### 零开销抽象

`GrSurfaceProxyPriv` 是零开销抽象：
- **无数据成员**: 只有一个指针
- **内联函数**: 所有方法都可能内联
- **按值返回优化**: 编译器通常优化为零开销
- **无虚函数**: 无虚函数表开销

### 内联 priv() 方法

```cpp
inline GrSurfaceProxyPriv GrSurfaceProxy::priv() {
    return GrSurfaceProxyPriv(this);
}
```

内联后等价于：
- 无额外函数调用开销
- 直接访问私有成员
- 编译时优化

### 临时对象优化

现代编译器对临时对象的优化：
- **RVO（Return Value Optimization）**: 消除临时对象
- **移动语义**: 快速转移所有权
- **内联**: 完全消除开销

典型用法：
```cpp
proxy->priv().doSomething();  // 零开销
```

### 直接访问私有成员

`*Priv` 方法直接访问私有成员：
```cpp
bool isExact() const { return SkBackingFit::kExact == fProxy->fFit; }
```

无需通过 getter 方法，避免额外的函数调用。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrSurfaceProxy.h` | 被访问类 | Proxy 主类 |
| `src/gpu/ganesh/GrSurfaceProxy.cpp` | 实现 | `exactify()` 和 `doLazyInstantiation()` 实现 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 使用者 | 调用 `doLazyInstantiation()` |
| `src/gpu/ganesh/GrResourceProvider.h` | 依赖 | 资源创建 |
| `src/gpu/ganesh/GrSurface.h` | 依赖 | Surface 类型 |
| `src/gpu/SkBackingFit.h` | 依赖 | Backing fit 枚举 |
| `src/gpu/ResourceKey.h` | 依赖 | Scratch key |
| `src/core/SkCanvasPriv.h` | 类似模式 | Canvas 的 Priv 类 |
| `src/gpu/ganesh/GrContextPriv.h` | 类似模式 | Context 的 Priv 类 |
