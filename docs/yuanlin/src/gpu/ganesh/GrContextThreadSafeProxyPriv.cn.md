# GrContextThreadSafeProxyPriv

> 源文件
> - src/gpu/ganesh/GrContextThreadSafeProxyPriv.h

## 概述

`GrContextThreadSafeProxyPriv` 是一个特权访问类（privileged accessor class），为 `GrContextThreadSafeProxy` 提供仅供 Skia 内部使用的方法。它采用"Priv"模式，是 Skia 中常见的一种设计模式，用于在不破坏封装的前提下向内部代码暴露额外的功能。

该类提供对线程安全上下文代理内部状态的访问，包括 GPU 能力（capabilities）、后端类型、上下文选项、文本 blob 重绘协调器、线程安全缓存等。这些功能对于 Skia 内部的上下文管理和资源协调至关重要，但不应该暴露给公共 API 的使用者。

## 架构位置

在 Skia 的 Ganesh GPU 渲染架构中，`GrContextThreadSafeProxyPriv` 位于上下文系统的核心：

```
GrContext_Base (基础上下文)
    └── GrContextThreadSafeProxy (线程安全代理)
        └── GrContextThreadSafeProxyPriv (特权访问器)
            ├── GrCaps (GPU 能力)
            ├── GrThreadSafePipelineBuilder (管线构建器)
            ├── TextBlobRedrawCoordinator (文本重绘协调器)
            └── GrThreadSafeCache (线程安全缓存)
```

该类充当内部代码访问代理对象私有成员的桥梁。

## 主要类与结构体

### GrContextThreadSafeProxyPriv

特权访问器类，提供对 `GrContextThreadSafeProxy` 内部状态的访问。

**继承关系：** 无继承，纯粹的访问器类。

**关键设计约束：**
- 不能有额外的数据成员
- 不能有虚函数
- 纯粹作为 `GrContextThreadSafeProxy` 的特权窗口

**成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fProxy` | `GrContextThreadSafeProxy*` | 指向被访问的代理对象 |

## 公共 API 函数

### 初始化

```cpp
void init(sk_sp<const GrCaps>, sk_sp<GrThreadSafePipelineBuilder>) const;
```

**功能：** 初始化线程安全代理的内部状态。

该方法设置代理的 GPU 能力和管线构建器，通常在上下文创建时调用。

### 上下文匹配

```cpp
bool matches(GrContext_Base* candidate) const;
```

**功能：** 检查给定的上下文是否与此代理关联。

**实现：**
```cpp
return fProxy == candidate->threadSafeProxy().get();
```

通过比较代理指针来判断上下文是否属于同一个线程安全代理。这用于验证上下文的所有权和关联关系。

### 后端访问

```cpp
GrBackend backend() const;
```

**功能：** 返回 GPU 后端类型（OpenGL、Vulkan、Metal 等）。

**实现：**
```cpp
return fProxy->fBackend;
```

### 选项访问

```cpp
const GrContextOptions& options() const;
```

**功能：** 返回上下文创建时使用的配置选项。

**实现：**
```cpp
return fProxy->fOptions;
```

这些选项控制各种行为，如着色器缓存、调试输出、资源限制等。

### 上下文 ID

```cpp
uint32_t contextID() const;
```

**功能：** 返回上下文的唯一标识符。

**实现：**
```cpp
return fProxy->fContextID;
```

该 ID 用于区分不同的上下文实例，特别是在多上下文应用中。

### GPU 能力访问

```cpp
const GrCaps* caps() const;
sk_sp<const GrCaps> refCaps() const;
```

**功能：** 获取 GPU 能力对象，描述 GPU 支持的特性和限制。

- `caps()`: 返回原始指针
- `refCaps()`: 返回智能指针，增加引用计数

GPU 能力信息包括：
- 支持的纹理格式
- 最大纹理大小
- 着色器特性
- 混合模式支持
- 等等

### 文本 Blob 重绘协调器

```cpp
sktext::gpu::TextBlobRedrawCoordinator* getTextBlobRedrawCoordinator();
const sktext::gpu::TextBlobRedrawCoordinator* getTextBlobRedrawCoordinator() const;
```

**功能：** 获取文本 blob 重绘协调器，用于管理文本渲染缓存。

文本 blob 重绘协调器负责：
- 缓存文本渲染结果
- 跟踪文本 blob 的使用
- 管理缓存失效
- 协调多线程访问

### 线程安全缓存

```cpp
GrThreadSafeCache* threadSafeCache();
const GrThreadSafeCache* threadSafeCache() const;
```

**功能：** 获取线程安全缓存，用于跨线程共享的资源缓存。

该缓存存储可以在多个上下文或线程间安全共享的资源，如预编译的着色器程序。

### 上下文放弃

```cpp
void abandonContext();
bool abandoned() const;
```

**功能：** 放弃上下文资源或查询放弃状态。

- `abandonContext()`: 标记上下文为已放弃，释放所有 GPU 资源
- `abandoned()`: 返回上下文是否已被放弃

放弃操作通常在 GPU 设备丢失或应用程序关闭时调用。

### 工厂方法

```cpp
static sk_sp<GrContextThreadSafeProxy> Make(GrBackendApi, const GrContextOptions&);
```

**功能：** 创建新的线程安全代理实例。

**参数：**
- `GrBackendApi`: GPU 后端类型
- `GrContextOptions`: 上下文配置选项

该方法是创建代理对象的标准入口点。

## 内部实现细节

### Priv 访问器模式

该类实现 Skia 的"Priv"模式，通过以下设计实现：

1. **友元关系**：
```cpp
friend class GrContextThreadSafeProxy;  // to construct/copy this type.
```

2. **私有构造函数**：
```cpp
explicit GrContextThreadSafeProxyPriv(GrContextThreadSafeProxy* proxy) : fProxy(proxy) {}
```

3. **禁止赋值**：
```cpp
GrContextThreadSafeProxyPriv& operator=(const GrContextThreadSafeProxyPriv&) = delete;
```

4. **禁止取地址**：
```cpp
const GrContextThreadSafeProxyPriv* operator&() const = delete;
GrContextThreadSafeProxyPriv* operator&() = delete;
```

### Priv 方法访问

`GrContextThreadSafeProxy` 提供 `priv()` 方法来获取特权访问器：

```cpp
inline GrContextThreadSafeProxyPriv GrContextThreadSafeProxy::priv() {
    return GrContextThreadSafeProxyPriv(this);
}

inline const GrContextThreadSafeProxyPriv GrContextThreadSafeProxy::priv() const {
    return GrContextThreadSafeProxyPriv(const_cast<GrContextThreadSafeProxy*>(this));
}
```

这允许代码通过 `proxy->priv().caps()` 的形式访问内部状态。

### Const 正确性

该类提供 const 和非 const 版本的访问方法，确保：
- Const 代理只能获得 const 访问
- 非 const 代理可以修改状态

注意 `priv() const` 的返回类型标记：
```cpp
// NOLINT(readability-const-return-type)
```

这抑制了关于按值返回 const 对象的警告，这在这种访问器模式中是必要的。

### 直接成员访问

该类通过直接访问 `fProxy` 的私有成员来提供功能：
```cpp
GrBackend backend() const { return fProxy->fBackend; }
const GrContextOptions& options() const { return fProxy->fOptions; }
```

这避免了额外的虚函数调用或间接层。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrContextThreadSafeProxy` | 被访问的主体类 |
| `GrContext_Base` | 基础上下文类 |
| `GrCaps` | GPU 能力描述 |
| `GrThreadSafePipelineBuilder` | 管线构建器 |
| `sktext::gpu::TextBlobRedrawCoordinator` | 文本渲染缓存 |
| `GrThreadSafeCache` | 线程安全缓存 |

### 被依赖的模块

`GrContextThreadSafeProxyPriv` 被 Skia 内部广泛使用：

| 模块 | 使用方式 |
|------|---------|
| `GrContext_Base` | 访问代理的内部状态 |
| `GrRecordingContext` | 获取能力和配置 |
| `GrDirectContext` | 初始化和管理代理 |
| `GrResourceCache` | 访问线程安全缓存 |
| GPU 后端实现 | 查询能力和选项 |

## 设计模式与设计决策

### Priv 访问器模式

这是 Skia 特有的设计模式，提供以下优势：
- 清晰的 API 边界（公共 vs 私有）
- 避免友元函数爆炸（每个需要访问的函数都是友元）
- 更好的代码组织（内部 API 集中在 Priv 类中）
- 编译时强制（不能从公共代码访问）

### 零开销抽象

该类设计为零开销抽象：
- 没有虚函数表
- 没有额外数据成员
- 按值返回（编译器可以优化）
- 内联方法

### 友元关系限制

通过限制友元关系到单一类（`GrContextThreadSafeProxy`），设计保持了封装性，只有代理自己可以创建 Priv 访问器。

### 禁止取地址

禁止取地址操作确保：
- 不能创建 Priv 对象的持久引用
- 强制通过 `proxy->priv()` 的模式使用
- 避免悬空指针问题

### Const 传播

提供 const 和非 const 版本确保 const 正确性从代理对象传播到访问器。

## 性能考量

### 内联优化

所有方法都定义在头文件中并标记为 `inline`（隐式或显式），编译器可以完全优化掉访问器对象：

```cpp
// 代码：
auto caps = proxy->priv().caps();

// 优化后可能等价于：
auto caps = proxy->fCaps.get();
```

### 零内存开销

Priv 对象只包含一个指针，且通常按值传递，编译器可以将其优化为寄存器传递或完全消除。

### 直接成员访问

通过直接访问成员而非调用方法，避免了函数调用开销（即使是虚函数调用）。

### 智能指针引用计数

`refCaps()` 返回智能指针涉及引用计数操作，但这在需要延长对象生命周期时是必要的。对于临时访问，应使用 `caps()` 返回原始指针。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/gpu/ganesh/GrContextThreadSafeProxy.h` | 主体类 | 被访问的线程安全代理 |
| `include/private/gpu/ganesh/GrContext_Base.h` | 依赖 | 基础上下文类 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | GPU 能力 |
| `src/text/gpu/TextBlobRedrawCoordinator.h` | 依赖 | 文本缓存协调器 |
| `src/gpu/ganesh/GrThreadSafeCache.h` | 依赖 | 线程安全缓存 |
| `include/gpu/ganesh/GrRecordingContext.h` | 使用者 | 通过 Priv 访问代理 |
| `include/gpu/ganesh/GrDirectContext.h` | 使用者 | 初始化和管理 |
