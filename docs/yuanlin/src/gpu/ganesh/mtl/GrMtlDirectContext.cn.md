# GrMtlDirectContext

> 源文件
> - include/gpu/ganesh/mtl/GrMtlDirectContext.h
> - src/gpu/ganesh/mtl/GrMtlDirectContext.mm

## 概述

`GrMtlDirectContext` 模块为 Ganesh 渲染引擎提供 Metal 后端的直接上下文（DirectContext）创建功能。该模块是 Skia 在 Apple 平台（macOS、iOS、tvOS）上使用 Metal 图形 API 的入口点，负责创建和初始化 Metal GPU 上下文。

直接上下文（Direct Context）是 Ganesh 架构中直接管理 GPU 资源和命令提交的上下文类型，与远程上下文（Remote Context）相对。

## 架构位置

该模块位于 Ganesh 上下文创建层的 Metal 实现：

```
Skia Graphics Library
└── GPU (Ganesh)
    ├── GrDirectContext           ← 抽象上下文接口
    └── Backend Implementations
        ├── Metal Backend
        │   ├── GrMtlDirectContext ← 当前模块（Metal 上下文创建）
        │   ├── GrMtlGpu           ← Metal GPU 实现
        │   └── GrMtlTrampoline    ← GPU 创建跳板
        ├── Vulkan Backend
        └── OpenGL Backend
```

## 主要类与结构体

该模块不定义新类，仅提供工厂函数。

## 公共 API 函数

### GrDirectContexts 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `sk_sp<GrDirectContext> MakeMetal(const GrMtlBackendContext&)` | 使用默认选项创建 Metal 上下文 |
| `sk_sp<GrDirectContext> MakeMetal(const GrMtlBackendContext&, const GrContextOptions&)` | 使用自定义选项创建 Metal 上下文 |

**参数说明**:
- `GrMtlBackendContext`: Metal 后端上下文配置，包含 `MTLDevice` 和 `MTLCommandQueue`
- `GrContextOptions`: Ganesh 上下文选项（缓存大小、调试选项等）

**返回值**:
- 成功: 返回 Metal GPU 上下文的智能指针
- 失败: 返回 `nullptr`（初始化失败）

## 内部实现细节

### 默认选项重载

提供便捷的默认选项版本：

```cpp
sk_sp<GrDirectContext> MakeMetal(const GrMtlBackendContext& backendContext) {
    GrContextOptions defaultOptions;
    return MakeMetal(backendContext, defaultOptions);
}
```

使用默认的 `GrContextOptions`，简化常见使用场景。

### Metal 上下文创建流程

完整的创建流程分为三个阶段：

**阶段 1: 创建上下文骨架**

```cpp
sk_sp<GrDirectContext> direct = GrDirectContextPriv::Make(
    GrBackendApi::kMetal,
    options,
    GrContextThreadSafeProxyPriv::Make(GrBackendApi::kMetal, options));
```

- 创建 `GrDirectContext` 对象
- 设置后端 API 类型为 Metal
- 创建线程安全代理对象（支持多线程访问）

**阶段 2: 创建并设置 GPU 对象**

```cpp
GrDirectContextPriv::SetGpu(
    direct,
    GrMtlTrampoline::MakeGpu(backendContext, options, direct.get()));
```

- 使用 `GrMtlTrampoline::MakeGpu` 创建 Metal GPU 实现
- 将 GPU 对象设置到上下文中
- `GrMtlTrampoline` 是 Objective-C++ 和 C++ 之间的桥接类

**阶段 3: 初始化上下文**

```cpp
if (!GrDirectContextPriv::Init(direct)) {
    return nullptr;
}
return direct;
```

- 调用 `Init` 完成上下文的最终初始化
- 初始化失败返回 `nullptr`

### Metal 后端上下文要求

`GrMtlBackendContext` 必须提供：

1. **MTLDevice**: Metal 设备对象
   - 客户端必须持有自己的引用
   - Ganesh 会创建额外的引用

2. **MTLCommandQueue**: Metal 命令队列
   - 客户端必须持有自己的引用
   - Ganesh 会创建额外的引用

3. **引用管理**:
   - 传入的对象必须有独立的引用计数
   - 销毁 `GrMtlBackendContext` 不会释放这些对象
   - 销毁 `GrDirectContext` 会释放 Ganesh 持有的引用

### 线程安全代理

创建线程安全代理支持跨线程访问：

```cpp
GrContextThreadSafeProxyPriv::Make(GrBackendApi::kMetal, options)
```

**功能**:
- 允许多线程查询上下文能力
- 支持跨线程创建资源
- 提供线程安全的缓存访问

### Objective-C++ 桥接

该文件使用 `.mm` 扩展名，支持 Objective-C++ 混合编程：
- 可以直接使用 Metal 的 Objective-C API
- 通过 `GrMtlTrampoline` 隔离 C++ 和 Objective-C++ 代码

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrDirectContext` | 提供上下文抽象接口 |
| `GrDirectContextPriv` | 访问上下文的私有构造和初始化 |
| `GrContextThreadSafeProxyPriv` | 创建线程安全代理 |
| `GrMtlBackendContext` | 定义 Metal 后端配置 |
| `GrMtlTrampoline` | 创建 Metal GPU 对象 |
| `GrContextOptions` | 定义上下文选项 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `SkSurface` | 创建 Metal 支持的绘制表面 |
| iOS/macOS 应用 | Apple 平台应用的 GPU 加速 |
| `GrContext` 测试 | 创建测试用 Metal 上下文 |
| Metal 互操作 | 与外部 Metal 资源交互 |

## 设计模式与设计决策

### 1. 工厂模式

`MakeMetal()` 函数是工厂方法，封装了复杂的上下文创建逻辑。

### 2. 构建器模式（隐式）

通过三阶段创建流程（Make → SetGpu → Init）逐步构建完整的上下文对象。

### 3. 外观模式

对外提供简单的 `MakeMetal()` 接口，隐藏内部的 `GrDirectContextPriv`、`GrMtlTrampoline` 等细节。

### 4. 代理模式

使用 `GrContextThreadSafeProxy` 提供线程安全的上下文访问代理。

### 5. 桥接模式

`GrMtlTrampoline` 作为桥接类，连接 C++ 的 Ganesh 架构和 Objective-C 的 Metal API。

### 6. 资源所有权分离

客户端和 Ganesh 分别持有 Metal 对象的引用，避免生命周期耦合。

## 性能考量

### 1. 引用计数开销

Metal 对象使用 ARC（Automatic Reference Counting），引用计数操作由编译器自动优化。

### 2. 上下文创建成本

上下文创建是重量级操作，应该：
- 在应用启动时创建一次
- 在应用生命周期内复用
- 避免频繁创建和销毁

### 3. 线程安全代理

线程安全代理使用原子操作保护共享状态，多线程访问有轻微开销。

### 4. GPU 对象延迟创建

实际的 GPU 资源在首次使用时才分配，减少初始化开销。

### 5. 命令队列复用

传入的 `MTLCommandQueue` 应该由客户端复用，避免频繁创建命令队列。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/GrDirectContext.h` | 直接上下文抽象接口 |
| `src/gpu/ganesh/GrDirectContextPriv.h` | 直接上下文私有访问接口 |
| `src/gpu/ganesh/GrContextThreadSafeProxyPriv.h` | 线程安全代理私有接口 |
| `include/gpu/ganesh/mtl/GrMtlBackendContext.h` | Metal 后端上下文定义 |
| `src/gpu/ganesh/mtl/GrMtlTrampoline.h` | Metal GPU 创建跳板 |
| `include/gpu/GrContextOptions.h` | 上下文选项定义 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h` | Metal GPU 实现 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端表面接口 |
