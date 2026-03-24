# GrContext_Base

> 源文件
> - src/gpu/ganesh/GrContext_Base.cpp

## 概述

`GrContext_Base` 是 Ganesh GPU 后端中所有上下文类的抽象基类。它提供了上下文的基础功能和共享状态，是 `GrRecordingContext` 和 `GrDirectContext` 等具体上下文类的共同基础。该类主要负责管理线程安全的上下文代理（`GrContextThreadSafeProxy`），并提供对 GPU 能力、后端类型和配置选项的访问。

该类的设计遵循"接口隔离原则"，将上下文的公共功能抽象到基类中，而将具体的实现细节留给派生类。它确保所有上下文类型都能提供一致的基础 API，同时保持各自的特殊性。

## 架构位置

在 Skia 的 Ganesh GPU 渲染架构中，`GrContext_Base` 位于上下文层次结构的根部：

```
GrContext_Base (基础上下文)
    ├── GrRecordingContext (录制上下文)
    │   ├── GrDDLContext (DDL 上下文)
    │   └── GrDirectContext (直接上下文)
    └── GrContextThreadSafeProxy (线程安全代理)
```

该类建立了上下文系统的基础架构，所有上下文类型都通过它访问共享的配置和能力。

## 主要类与结构体

### GrContext_Base

所有 GPU 上下文的抽象基类。

**继承关系：** 基类，无父类（除了隐式的对象基类）。

**关键成员变量：**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fThreadSafeProxy` | `sk_sp<GrContextThreadSafeProxy>` | 线程安全的上下文代理，包含共享的配置和能力 |

该类的设计非常简洁，几乎所有状态都委托给线程安全代理。

## 公共 API 函数

### 构造函数

```cpp
GrContext_Base::GrContext_Base(sk_sp<GrContextThreadSafeProxy> proxy)
        : fThreadSafeProxy(std::move(proxy))
```

**功能：** 创建基础上下文对象。

**参数：**
- `proxy`: 线程安全的上下文代理，包含共享配置

该构造函数是 protected 的，只能由派生类调用。

### 初始化

```cpp
bool GrContext_Base::init();
```

**功能：** 初始化上下文的基础功能。

**实现：**
```cpp
SkASSERT(fThreadSafeProxy->isValid());
return true;
```

当前实现只验证代理的有效性。派生类可能会扩展此方法以执行额外的初始化。

### 上下文 ID

```cpp
uint32_t GrContext_Base::contextID() const;
```

**功能：** 返回上下文的唯一标识符。

**实现：**
```cpp
return fThreadSafeProxy->priv().contextID();
```

通过代理获取上下文 ID，用于区分不同的上下文实例。

### 后端类型

```cpp
GrBackendApi GrContext_Base::backend() const;
```

**功能：** 返回 GPU 后端类型（OpenGL、Vulkan、Metal、Direct3D 等）。

**实现：**
```cpp
return fThreadSafeProxy->priv().backend();
```

### 配置选项

```cpp
const GrContextOptions& GrContext_Base::options() const;
```

**功能：** 返回上下文创建时使用的配置选项。

**实现：**
```cpp
return fThreadSafeProxy->priv().options();
```

配置选项包括：
- 着色器缓存设置
- 资源限制
- 调试选项
- 性能调优参数

### GPU 能力

```cpp
const GrCaps* GrContext_Base::caps() const;
sk_sp<const GrCaps> GrContext_Base::refCaps() const;
```

**功能：** 获取 GPU 能力对象。

**实现：**
```cpp
return fThreadSafeProxy->priv().caps();
return fThreadSafeProxy->priv().refCaps();
```

- `caps()`: 返回原始指针，用于临时访问
- `refCaps()`: 返回智能指针，用于需要延长生命周期的场景

### 默认后端格式

```cpp
GrBackendFormat GrContext_Base::defaultBackendFormat(SkColorType skColorType,
                                                     GrRenderable renderable) const;
```

**功能：** 获取给定 Skia 颜色类型的默认后端格式。

**实现：**
```cpp
return fThreadSafeProxy->defaultBackendFormat(skColorType, renderable);
```

该方法将 Skia 的 CPU 颜色类型映射到 GPU 后端的纹理格式，例如：
- `kRGBA_8888_SkColorType` → OpenGL 的 `GL_RGBA8`
- `kBGRA_8888_SkColorType` → Vulkan 的 `VK_FORMAT_B8G8R8A8_UNORM`

**参数：**
- `skColorType`: Skia 颜色类型
- `renderable`: 是否需要作为渲染目标

### 压缩格式

```cpp
GrBackendFormat GrContext_Base::compressedBackendFormat(SkTextureCompressionType c) const;
```

**功能：** 获取给定压缩类型的后端格式。

**实现：**
```cpp
return fThreadSafeProxy->compressedBackendFormat(c);
```

支持的压缩格式包括：
- ETC1
- BC1 (DXT1)
- ASTC
- 等等

### 最大采样数

```cpp
int GrContext_Base::maxSurfaceSampleCountForColorType(SkColorType colorType) const;
```

**功能：** 返回给定颜色类型的最大支持采样数（用于 MSAA 抗锯齿）。

**实现：**
```cpp
return fThreadSafeProxy->maxSurfaceSampleCountForColorType(colorType);
```

返回值示例：
- 0 或 1：不支持 MSAA
- 4：支持 4x MSAA
- 8：支持 8x MSAA
- 16：支持 16x MSAA

### 线程安全代理

```cpp
sk_sp<GrContextThreadSafeProxy> GrContext_Base::threadSafeProxy();
```

**功能：** 获取线程安全代理的引用。

**实现：**
```cpp
return fThreadSafeProxy;
```

返回智能指针，增加引用计数。

## 内部实现细节

### 委托模式

`GrContext_Base` 使用委托模式，将几乎所有功能委托给 `GrContextThreadSafeProxy`：

```cpp
uint32_t contextID() const { return fThreadSafeProxy->priv().contextID(); }
GrBackendApi backend() const { return fThreadSafeProxy->priv().backend(); }
const GrCaps* caps() const { return fThreadSafeProxy->priv().caps(); }
// 等等
```

这种设计有以下优势：
- 线程安全：代理包含的状态可以安全地跨线程访问
- 共享状态：多个上下文可以共享同一个代理
- 简化实现：基类不需要管理复杂的状态

### GrBaseContextPriv 实现

文件末尾包含 `GrBaseContextPriv` 的实现，这是另一个 Priv 访问器：

#### 引用能力

```cpp
sk_sp<const GrCaps> GrBaseContextPriv::refCaps() const {
    return this->context()->refCaps();
}
```

**功能：** 通过 Priv 接口获取能力的引用。

这是 Priv 模式的一部分，允许内部代码访问基础上下文的功能。

#### 着色器错误处理器

```cpp
GrContextOptions::ShaderErrorHandler* GrBaseContextPriv::getShaderErrorHandler() const {
    const GrContextOptions& options(this->options());
    return options.fShaderErrorHandler ? options.fShaderErrorHandler
                                       : skgpu::DefaultShaderErrorHandler();
}
```

**功能：** 获取着色器错误处理器。

如果用户提供了自定义处理器，使用用户的；否则使用默认处理器。这确保着色器编译错误总是有地方报告。

### 析构函数

```cpp
GrContext_Base::~GrContext_Base() { }
```

虚析构函数（隐式虚拟），确保派生类可以正确清理资源。实现为空，因为所有资源由智能指针管理。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrContextThreadSafeProxy` | 线程安全代理，包含共享配置 |
| `GrCaps` | GPU 能力描述 |
| `GrBackendSurface` | 后端表面格式 |
| `GrContextOptions` | 上下文配置选项 |
| `ShaderErrorHandler` | 着色器错误处理 |
| `GrBaseContextPriv` | 基础上下文的 Priv 访问器 |
| `GrContextThreadSafeProxyPriv` | 代理的 Priv 访问器 |

### 被依赖的模块

`GrContext_Base` 是许多上下文类的基础：

| 模块 | 使用方式 |
|------|---------|
| `GrRecordingContext` | 派生自基类 |
| `GrDirectContext` | 通过 `GrRecordingContext` 间接派生 |
| `GrDDLContext` | 通过 `GrRecordingContext` 派生 |
| 所有使用上下文的代码 | 通过基类接口访问 |

## 设计模式与设计决策

### 委托模式

将大部分功能委托给 `GrContextThreadSafeProxy`，这是一种组合优于继承的例子。代理包含所有共享状态，基类只是提供方便的访问方法。

### 模板方法模式

`init()` 方法是模板方法模式的体现，基类提供基础实现，派生类可以扩展：
```cpp
bool DerivedContext::init() {
    if (!INHERITED::init()) {
        return false;
    }
    // 派生类特定的初始化
    return true;
}
```

### 最小化基类

基类保持最小化，只包含所有上下文类型都需要的功能。这遵循"接口隔离原则"。

### 智能指针所有权

使用 `sk_sp` 管理代理的生命周期，确保：
- 自动引用计数
- 异常安全
- 无内存泄漏

### Priv 访问器集成

与 `GrBaseContextPriv` 和 `GrContextThreadSafeProxyPriv` 配合，提供清晰的 API 边界。

## 性能考量

### 委托开销

所有方法调用都通过代理，涉及一次额外的间接访问：
```cpp
caps() → fThreadSafeProxy->priv().caps() → fProxy->fCaps.get()
```

但由于方法通常是内联的，编译器可以优化掉中间层。

### 智能指针开销

使用 `sk_sp` 涉及引用计数操作，但：
- 引用计数在多线程场景中是必要的
- 原子操作在现代 CPU 上很快
- 避免手动内存管理的错误

### 虚析构函数

虽然有虚析构函数（隐式），但这只在对象销毁时调用一次，开销可忽略。

### 能力查询缓存

GPU 能力对象被代理缓存，多次查询不需要重复计算。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `include/private/gpu/ganesh/GrContext_Base.h` | 头文件 | 类定义 |
| `include/gpu/ganesh/GrContextThreadSafeProxy.h` | 依赖 | 线程安全代理 |
| `src/gpu/ganesh/GrCaps.h` | 依赖 | GPU 能力 |
| `include/gpu/ganesh/GrBackendSurface.h` | 依赖 | 后端格式 |
| `include/gpu/ganesh/GrContextOptions.h` | 依赖 | 配置选项 |
| `src/gpu/ganesh/GrBaseContextPriv.h` | 依赖 | Priv 访问器 |
| `src/gpu/ganesh/GrContextThreadSafeProxyPriv.h` | 依赖 | 代理 Priv 访问器 |
| `include/gpu/ganesh/GrRecordingContext.h` | 派生类 | 录制上下文 |
| `include/gpu/ganesh/GrDirectContext.h` | 派生类 | 直接上下文 |
| `include/gpu/ShaderErrorHandler.h` | 依赖 | 错误处理 |
