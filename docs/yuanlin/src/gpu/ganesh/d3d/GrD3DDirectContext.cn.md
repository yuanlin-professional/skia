# GrD3DDirectContext

> 源文件
> - include/gpu/ganesh/d3d/GrD3DDirectContext.h
> - src/gpu/ganesh/d3d/GrD3DDirectContext.cpp

## 概述

`GrD3DDirectContext` 模块提供了创建 Direct3D 12 后端 `GrDirectContext` 的工厂函数。该模块是 Skia Ganesh GPU 后端对 Microsoft Direct3D 12 图形 API 的入口点,使得 Skia 能够在 Windows 平台上利用 D3D12 进行硬件加速渲染。

该模块的功能类似于 OpenGL 版本的 `GrGLDirectContext`,但专门针对 D3D12 后端。它接受 `GrD3DBackendContext` 作为输入,该结构包含 D3D12 设备、命令队列等必要的 Direct3D 对象,并将其封装为 Skia 的统一上下文接口。

## 架构位置

在 Skia GPU 初始化流程中的位置:

```
应用程序(Windows)
    ↓
创建 D3D12 设备和队列
    ↓
GrDirectContexts::MakeD3D ← 当前模块
    ↓
├─ 创建 GrDirectContext 框架
├─ 创建 GrD3DGpu 实例
└─ 初始化上下文
    ↓
GrDirectContext (D3D12 后端)
    ↓
绘制管道 (SkCanvas, SkSurface)
```

## 主要类与结构体

该模块不定义类,仅提供命名空间函数。

### GrDirectContexts 命名空间

包含 Direct3D 上下文创建函数。

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `sk_sp<GrDirectContext> MakeD3D(const GrD3DBackendContext&)` | 使用默认选项从 D3D 后端上下文创建 Skia 上下文 |
| `sk_sp<GrDirectContext> MakeD3D(const GrD3DBackendContext&, const GrContextOptions&)` | 使用自定义选项从 D3D 后端上下文创建 Skia 上下文 |

### 函数参数说明

- `backendContext`: `GrD3DBackendContext` 引用,包含 D3D12 设备、队列、内存分配器等
- `options`: `GrContextOptions` 引用,配置上下文行为(可选)

## 内部实现细节

### 主要创建函数实现

```cpp
sk_sp<GrDirectContext> MakeD3D(const GrD3DBackendContext& backendContext,
                               const GrContextOptions& options) {
    // 1. 创建上下文框架
    auto direct = GrDirectContextPriv::Make(
            GrBackendApi::kDirect3D,
            options,
            GrContextThreadSafeProxyPriv::Make(GrBackendApi::kDirect3D, options));

    // 2. 创建 D3D12 GPU 实例
    GrDirectContextPriv::SetGpu(direct,
                                GrD3DGpu::Make(backendContext, options, direct.get()));

    // 3. 初始化上下文
    if (!GrDirectContextPriv::Init(direct)) {
        return nullptr;
    }

    return direct;
}
```

### 简化版本

```cpp
sk_sp<GrDirectContext> MakeD3D(const GrD3DBackendContext& backendContext) {
    GrContextOptions defaultOptions;
    return GrDirectContexts::MakeD3D(backendContext, defaultOptions);
}
```

提供便利接口,使用默认配置。

### 初始化流程

1. **创建上下文框架**: 调用 `GrDirectContextPriv::Make` 创建基础上下文结构
2. **指定后端类型**: 使用 `GrBackendApi::kDirect3D` 标识
3. **创建线程安全代理**: 用于跨线程共享上下文信息
4. **创建 GPU 实例**: 调用 `GrD3DGpu::Make` 创建 D3D12 特定的 GPU 实现
5. **关联 GPU**: 将 GPU 实例设置到上下文中
6. **执行初始化**: 调用 `GrDirectContextPriv::Init` 完成能力检测和资源分配
7. **处理失败**: 如果初始化失败,返回 nullptr

### GrD3DBackendContext 的角色

`GrD3DBackendContext` 是外部提供的结构,包含:
- `ID3D12Device*`: D3D12 设备对象
- `ID3D12CommandQueue*`: 命令队列
- `GrD3DMemoryAllocator*`: 内存分配器(可选)
- 其他 D3D12 初始化信息

应用程序需要在调用 `MakeD3D` 之前正确初始化这些对象。

### 生命周期管理

注释中特别强调:

> The Direct3D context must be kept alive until the returned GrDirectContext is first destroyed or abandoned.

这意味着应用程序需要确保:
1. 在 `GrDirectContext` 销毁之前,不销毁 D3D12 设备和队列
2. 或者调用 `abandonContext()` 通知 Skia 放弃该上下文

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `GrDirectContext` | 目标上下文类 |
| `GrDirectContextPriv` | 上下文私有实现辅助 |
| `GrD3DGpu` | Direct3D 12 GPU 实现 |
| `GrD3DBackendContext` | D3D12 后端上下文结构 |
| `GrContextOptions` | 上下文配置选项 |
| `GrContextThreadSafeProxyPriv` | 线程安全代理私有实现 |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| Windows 应用程序 | 初始化 Skia D3D12 渲染 |
| UWP 应用 | Universal Windows Platform 图形渲染 |
| 游戏引擎(Windows) | 使用 D3D12 的游戏引擎集成 Skia |
| 测试和基准测试 | D3D12 后端性能测试 |

## 设计模式与设计决策

### 工厂方法模式

静态工厂函数封装复杂的上下文创建过程,与其他后端(OpenGL、Vulkan、Metal)保持一致的接口风格。

### 重载提供便利性

提供带选项和不带选项两个版本:
- 简单场景:使用默认配置
- 高级场景:自定义缓存大小、调试选项等

### 分离关注点

模块本身不创建 D3D12 对象,而是接受现有的 `GrD3DBackendContext`:
- 应用程序负责 D3D12 初始化和生命周期管理
- Skia 负责利用这些对象进行渲染
- 清晰的职责边界

### 失败透明处理

如果初始化失败(例如不支持的硬件或驱动版本),返回 `nullptr`,调用者需要处理:

```cpp
auto context = GrDirectContexts::MakeD3D(backendContext, options);
if (!context) {
    // 处理初始化失败
}
```

### 智能指针管理生命周期

返回 `sk_sp<GrDirectContext>`,自动管理引用计数,避免内存泄漏。

### 与其他后端一致的 API

函数命名和参数结构与 `MakeGL`、`MakeVulkan`、`MakeMetal` 保持一致:

```cpp
// 一致的 API 模式
GrDirectContexts::MakeGL(glInterface, options);
GrDirectContexts::MakeVulkan(vkBackendContext, options);
GrDirectContexts::MakeMetal(mtlDevice, mtlQueue, options);
GrDirectContexts::MakeD3D(d3dBackendContext, options);
```

## 性能考量

### 一次性初始化

上下文创建是一次性操作,性能不是主要考虑因素。

### 零拷贝传递

`backendContext` 通过引用传递,避免拷贝:

```cpp
sk_sp<GrDirectContext> MakeD3D(const GrD3DBackendContext& backendContext, ...)
```

### 最小化中间对象

直接创建 GPU 实例并关联,无不必要的临时对象。

### 快速失败路径

如果初始化失败,及时返回 `nullptr`,不占用资源。

### 内联优化

简单的重载函数可以被编译器内联。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/gpu/ganesh/GrDirectContext.h` | 目标上下文类定义 |
| `src/gpu/ganesh/GrDirectContextPriv.h` | 上下文私有实现 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | Direct3D 12 GPU 实现 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | D3D12 类型定义 |
| `include/gpu/ganesh/d3d/GrD3DBackendContext.h` | D3D12 后端上下文结构 |
| `include/gpu/ganesh/GrContextOptions.h` | 上下文配置选项 |
| `src/gpu/ganesh/GrContextThreadSafeProxyPriv.h` | 线程安全代理私有接口 |
| `src/gpu/ganesh/d3d/GrD3DResourceProvider.h` | D3D12 资源管理 |
| `src/gpu/ganesh/d3d/GrD3DCaps.h` | D3D12 能力检测 |
