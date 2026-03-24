# GrTextureRenderTargetProxy

> 源文件: src/gpu/ganesh/GrTextureRenderTargetProxy.h, src/gpu/ganesh/GrTextureRenderTargetProxy.cpp

## 概述

`GrTextureRenderTargetProxy` 是 Ganesh GPU 后端中的一个核心代理类，它同时继承自 `GrRenderTargetProxy` 和 `GrTextureProxy`，用于表示既可以作为渲染目标又可以作为纹理使用的 GPU 资源。这种双重身份的设计使得渲染结果可以直接作为纹理在后续渲染流程中使用，这在现代图形管线中非常常见（如后处理效果、阴影贴图等）。

该类采用延迟实例化策略，只在真正需要时才分配底层的 GPU 资源，从而优化内存使用和性能。它支持三种创建模式：延迟版本（deferred）、惰性回调版本（lazy-callback）和包装版本（wrapped）。

## 架构位置

`GrTextureRenderTargetProxy` 位于 Skia 图形库的 GPU 渲染架构中，具体位置如下：

```
Skia
└── src/gpu/ganesh/           # Ganesh GPU 后端
    ├── GrSurfaceProxy        # 抽象基类，所有代理的根
    ├── GrTextureProxy        # 纹理代理
    ├── GrRenderTargetProxy   # 渲染目标代理
    └── GrTextureRenderTargetProxy  # 纹理+渲染目标代理（本类）
```

该类通过虚继承机制同时继承了纹理和渲染目标的功能，处于 GPU 资源管理体系的核心位置。

## 主要类与结构体

### 继承关系

```
GrSurfaceProxy (虚基类)
    ↑
    ├── GrTextureProxy
    ↑       ↑
    │       └─────┐
    │             │
    ├── GrRenderTargetProxy
                  ↑
                  │
        GrTextureRenderTargetProxy
```

### 关键成员变量

该类没有自己独有的成员变量，所有状态由其基类管理：

| 成员变量 | 类型 | 来源基类 | 说明 |
|---------|------|---------|------|
| fMipmapped | skgpu::Mipmapped | GrTextureProxy | 是否包含 mipmap |
| fMipmapStatus | GrMipmapStatus | GrTextureProxy | Mipmap 状态 |
| fSampleCnt | int | GrRenderTargetProxy | 多重采样数量 |
| fSurfaceFlags | GrInternalSurfaceFlags | GrSurfaceProxy | 表面标志位 |
| fTarget | sk_sp&lt;GrSurface&gt; | GrSurfaceProxy | 实际的 GPU 资源 |

## 公共 API 函数

由于 `GrTextureRenderTargetProxy` 主要通过友元类 `GrProxyProvider` 和 `GrSurfaceProxy` 创建，其构造函数都是私有的。该类没有声明新的公共方法，所有公共接口都继承自基类。

### 主要继承的公共接口

- `asTextureProxy()` / `asRenderTargetProxy()`: 类型转换接口
- `instantiate(GrResourceProvider*)`: 实例化底层资源
- `isInstantiated()`: 检查是否已实例化
- `dimensions()`, `backendFormat()`: 获取资源属性
- `numSamples()`: 获取采样数（来自 RenderTarget）
- `mipmapped()`: 获取 mipmap 状态（来自 Texture）

## 内部实现细节

### 构造函数实现

该类提供三种构造方式：

**1. 延迟版本（Deferred）**
```cpp
GrTextureRenderTargetProxy(const GrCaps&, const GrBackendFormat&,
                           SkISize, int sampleCnt, skgpu::Mipmapped, ...)
```
- 用于已知资源参数但还未创建 GPU 资源的情况
- 会调用 `initSurfaceFlags()` 初始化标志位
- 如果是 MSAA 且不支持自动解析，会设置手动解析标志

**2. 惰性回调版本（Lazy-callback）**
```cpp
GrTextureRenderTargetProxy(const GrCaps&, LazyInstantiateCallback&&, ...)
```
- 用于延迟决定资源参数的情况（如动态大小的图集）
- 将回调传递给虚基类 `GrSurfaceProxy`
- 向子类传递空回调以正确路由到相应构造函数

**3. 包装版本（Wrapped）**
```cpp
GrTextureRenderTargetProxy(sk_sp<GrSurface>, UseAllocator, GrDDLProvider)
```
- 用于包装已存在的 GPU 资源
- 确保资源同时具有纹理和渲染目标能力
- 验证 MSAA 解析策略的一致性

### 核心方法实现

**initSurfaceFlags()**
- 处理 MSAA 手动解析标志的设置
- 对于 MSAA 纹理渲染目标，如果硬件不支持自动解析，需要设置 `kRequiresManualMSAAResolve` 标志
- 这是唯一需要在代理级别设置该标志的情况

**onUninstantiatedGpuMemorySize()**
- 计算未实例化时的预估 GPU 内存大小
- MSAA 情况下会额外加上解析缓冲区的大小（+1 样本）
- 考虑 mipmap 和精确尺寸标志

**instantiate()**
- 实际创建底层 GPU 资源
- 使用 `instantiateImpl()` 同时创建纹理和渲染目标
- 验证创建结果同时具有纹理和渲染目标能力

**callbackDesc()**
- 为惰性实例化提供描述信息
- 返回 `LazySurfaceDesc` 结构，包含维度、适配方式、可渲染标志等
- 支持完全惰性代理（维度为 -1）

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|-----|---------|------|
| GrTextureProxy | 继承 | 提供纹理代理功能 |
| GrRenderTargetProxy | 继承 | 提供渲染目标代理功能 |
| GrSurfaceProxy | 虚继承 | 提供基础代理功能 |
| GrCaps | 使用 | 查询硬件能力 |
| GrResourceProvider | 使用 | 创建实际 GPU 资源 |
| GrSurface | 使用 | 实际的 GPU 表面对象 |
| GrTexture | 使用 | 纹理资源 |
| GrRenderTarget | 使用 | 渲染目标资源 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|-----|---------|------|
| GrProxyProvider | 创建 | 通过工厂方法创建实例 |
| GrSurfaceDrawContext | 使用 | 用于需要渲染和纹理双重功能的绘制上下文 |
| GrRenderTaskDAG | 管理 | 在渲染任务图中作为资源节点 |

## 设计模式与设计决策

### 虚继承（Virtual Inheritance）

采用虚继承解决菱形继承问题：
- `GrTextureProxy` 和 `GrRenderTargetProxy` 都继承自 `GrSurfaceProxy`
- 使用虚继承确保只有一个 `GrSurfaceProxy` 实例
- 构造函数必须显式调用虚基类构造函数

### Windows 警告抑制

代码中使用编译器指令抑制 Windows 的 C4250 警告：
```cpp
#pragma warning(disable: 4250)
```
这是因为虚继承导致的 `asTextureProxy()` 和 `asRenderTargetProxy()` 的"支配继承"（dominance）警告。

### 延迟实例化模式

- 代理对象的 uniqueID 通常与实际资源的 uniqueID 不同
- 这允许资源复用和更灵活的内存管理
- 支持 DDL（Deferred Display List）录制

### 友元类设计

通过友元类控制对象创建，确保：
- 只有 `GrProxyProvider` 可以创建实例
- 强制使用工厂模式，统一管理资源创建

## 性能考量

### 内存优化

1. **延迟分配**: 只在真正需要时才分配 GPU 内存
2. **资源复用**: 通过代理模式允许多个上下文共享资源
3. **MSAA 解析缓冲区**: 准确计算包含解析缓冲区的内存大小

### MSAA 性能

- 检测硬件是否支持自动 MSAA 解析（如 `GL_EXT_multisampled_render_to_texture`）
- 不支持时需要手动解析，会影响性能
- 通过标志位提前标记，避免运行时检测

### 内存估算精度

`onUninstantiatedGpuMemorySize()` 考虑：
- 样本数（MSAA）
- Mipmap 级别
- 精确/近似尺寸配置
- 解析缓冲区开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrSurfaceProxy.h | 基类 | 代理基类定义 |
| src/gpu/ganesh/GrTextureProxy.h | 基类 | 纹理代理定义 |
| src/gpu/ganesh/GrRenderTargetProxy.h | 基类 | 渲染目标代理定义 |
| src/gpu/ganesh/GrTexture.h | 使用 | 实际纹理资源 |
| src/gpu/ganesh/GrRenderTarget.h | 使用 | 实际渲染目标资源 |
| src/gpu/ganesh/GrProxyProvider.h | 工厂 | 创建代理的工厂类 |
| src/gpu/ganesh/GrResourceProvider.h | 使用 | 创建实际 GPU 资源 |
| src/gpu/ganesh/GrCaps.h | 使用 | GPU 能力查询 |
