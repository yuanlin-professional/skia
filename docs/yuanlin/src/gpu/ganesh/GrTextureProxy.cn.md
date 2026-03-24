# GrTextureProxy

> 源文件: src/gpu/ganesh/GrTextureProxy.h, src/gpu/ganesh/GrTextureProxy.cpp

## 概述

`GrTextureProxy` 是 Ganesh GPU 后端中纹理资源的延迟实例化代理类。它虚继承自 `GrSurfaceProxy`，代表一个尚未创建或已经创建的 GPU 纹理资源。该类的核心设计理念是延迟分配（deferred allocation）：在实际需要纹理之前，只维护纹理的描述信息，直到渲染时才真正分配 GPU 内存。

这种设计带来多个优势：优化内存使用、支持 DDL（Deferred Display List）录制、允许资源共享和复用。`GrTextureProxy` 还负责管理纹理的 mipmap 状态、unique key 以及延迟上传数据。

## 架构位置

`GrTextureProxy` 位于 Skia GPU 资源管理的代理层：

```
Skia GPU 资源管理
├── 资源层（Resource Layer）
│   └── GrTexture                    # 实际的 GPU 纹理
└── 代理层（Proxy Layer）
    └── GrSurfaceProxy               # 表面代理基类
        ├── GrTextureProxy           # 纹理代理（本类）
        ├── GrRenderTargetProxy      # 渲染目标代理
        └── GrTextureRenderTargetProxy  # 组合代理
```

在渲染流程中的位置：
```
应用代码 → GrTextureProxy → GrTexture → GPU 驱动
          (延迟描述)    (实际资源)   (硬件)
```

## 主要类与结构体

### 继承关系

```
GrSurfaceProxy (虚基类)
    ↑
    │ (虚继承)
    │
GrTextureProxy
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fMipmapped | skgpu::Mipmapped | 是否包含 mipmap（创建时的设置） |
| fMipmapStatus | GrMipmapStatus | Mipmap 当前状态（NotAllocated/Dirty/Valid） |
| fInitialMipmapStatus | GrMipmapStatus | 初始 mipmap 状态（调试用） |
| fSyncTargetKey | bool | 是否将 unique key 同步到实际纹理 |
| fCreatingProvider | GrDDLProvider | 创建提供者（DDL 或普通） |
| fUniqueKey | skgpu::UniqueKey | 唯一键，用于缓存查找 |
| fProxyProvider | GrProxyProvider* | 代理提供者指针（仅当有 unique key 时） |
| fDeferredUploader | unique_ptr&lt;GrDeferredProxyUploader&gt; | 延迟上传器 |

### 辅助类

**GrTextureProxyPriv**：提供特权访问接口
- 管理延迟上传器
- 调度上传操作

**GrTextureProxy::CacheAccess**：缓存访问接口
- 设置/清除 unique key

## 公共 API 函数

### 类型转换

```cpp
GrTextureProxy* asTextureProxy() override
const GrTextureProxy* asTextureProxy() const override
```

### 实例化

```cpp
bool instantiate(GrResourceProvider*) override
```
实例化底层纹理资源。对于非惰性代理，调用 `instantiateImpl()` 创建纹理。

### Mipmap 查询

```cpp
skgpu::Mipmapped mipmapped() const
skgpu::Mipmapped proxyMipmapped() const
bool mipmapsAreDirty() const
```
- `mipmapped()`: 如果已实例化，返回实际纹理的状态；否则返回代理的设置
- `proxyMipmapped()`: 总是返回创建时的设置
- `mipmapsAreDirty()`: 检查 mipmap 是否需要重新生成

### Mipmap 状态管理

```cpp
void markMipmapsDirty()
void markMipmapsClean()
```

### 纹理类型

```cpp
GrTextureType textureType() const
bool hasRestrictedSampling() const
```

### Unique Key 管理

```cpp
const skgpu::UniqueKey& getUniqueKey() const override
```

### 静态工具函数

```cpp
static bool ProxiesAreCompatibleAsDynamicState(
    const GrSurfaceProxy* first,
    const GrSurfaceProxy* second)
```
检查两个代理是否可以作为动态状态一起刷新到 GPU。

## 内部实现细节

### 构造函数

**1. 延迟版本（Deferred）**：
```cpp
GrTextureProxy(const GrBackendFormat&, SkISize, skgpu::Mipmapped,
              GrMipmapStatus, SkBackingFit, skgpu::Budgeted, ...)
```
- 用于已知参数但未创建资源的情况
- 初始化 mipmap 状态
- 外部纹理自动标记为只读

**2. 惰性回调版本（Lazy-callback）**：
```cpp
GrTextureProxy(LazyInstantiateCallback&&, const GrBackendFormat&, ...)
```
- 用于延迟决定参数的情况
- 回调在实际需要时调用

**3. 包装版本（Wrapped）**：
```cpp
GrTextureProxy(sk_sp<GrSurface>, UseAllocator, GrDDLProvider)
```
- 包装已存在的纹理
- 继承纹理的 mipmap 状态
- 如果纹理有 unique key，将其转移到代理

### 析构函数

```cpp
~GrTextureProxy()
```

**清理流程**：
1. 将 `fTarget` 置零（可能已被清理）
2. 如果有 unique key 且 `fProxyProvider` 有效：
   - 调用 `processInvalidUniqueKey()`（不删除 GPU 资源）
3. DDL 模式下的代理保留 key

### instantiate 实现

```cpp
bool instantiate(GrResourceProvider* resourceProvider)
```

**逻辑**：
1. 检查是否为惰性代理（惰性代理返回 false）
2. 调用 `instantiateImpl()` 创建纹理：
   - 样本数：1（纹理不做 MSAA）
   - 可渲染性：`GrRenderable::kNo`
   - Mipmap：使用 `fMipmapped`
   - Unique key：如果有效则传递
3. 验证结果（断言有纹理但无渲染目标）

### createSurface 实现

```cpp
sk_sp<GrSurface> createSurface(GrResourceProvider*) const override
```

使用 `createSurfaceImpl()` 创建，参数固定：
- 样本数：1
- 可渲染性：`kNo`
- Mipmap：`fMipmapped`

### Unique Key 管理

**setUniqueKey()**：
```cpp
void setUniqueKey(GrProxyProvider* proxyProvider,
                 const skgpu::UniqueKey& key)
```

**流程**：
1. 断言 key 有效且代理尚未有 key
2. 如果已实例化且 `fSyncTargetKey` 为 true：
   - 将 key 设置到底层纹理
3. 保存 key 和 provider 指针

**clearUniqueKey()**：
- 重置 key 和 provider 指针
- 不影响底层纹理的 key

### callbackDesc 实现

为惰性实例化提供描述信息：
```cpp
LazySurfaceDesc callbackDesc() const override
```

返回结构包含：
- 维度（完全惰性时为 -1）
- 适配方式（Exact 或 Approx）
- 可渲染性：`kNo`
- Mipmap：`fMipmapped`
- 样本数：1
- 后端格式和纹理类型

### ProxiesAreCompatibleAsDynamicState 实现

```cpp
bool ProxiesAreCompatibleAsDynamicState(const GrSurfaceProxy* first,
                                       const GrSurfaceProxy* second)
```

检查两个条件：
1. 纹理类型相同（`textureType()`）
2. 后端格式相同（`backendFormat()`）

这确保它们可以在同一绘制调用中作为不同纹理槽使用。

### 延迟上传支持

**GrTextureProxyPriv 方法**：

```cpp
void setDeferredUploader(unique_ptr<GrDeferredProxyUploader> uploader)
```
附加延迟上传器（通常在工作线程准备数据时使用）。

```cpp
void scheduleUpload(GrOpFlushState* flushState)
```
调度 ASAP 上传（如果已实例化且有上传器）。

```cpp
void resetDeferredUploader()
```
清除上传器（上传完成后释放 CPU 数据）。

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|-----|---------|------|
| GrSurfaceProxy | 继承 | 表面代理基类 |
| GrTexture | 使用 | 实际纹理资源 |
| GrResourceProvider | 使用 | 创建 GPU 资源 |
| GrProxyProvider | 使用 | 管理代理生命周期 |
| GrDeferredProxyUploader | 使用 | 延迟数据上传 |
| skgpu::UniqueKey | 使用 | 资源唯一标识 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|-----|---------|------|
| GrTextureRenderTargetProxy | 继承 | 可渲染纹理代理 |
| GrProxyProvider | 创建 | 工厂创建代理 |
| GrSurfaceProxyView | 组合 | 代理视图（proxy + origin + swizzle） |
| GrThreadSafeCache | 存储 | 线程安全的代理缓存 |

## 设计模式与设计决策

### 代理模式（Proxy Pattern）

`GrTextureProxy` 作为 `GrTexture` 的代理：
- 提供相同的接口抽象
- 控制资源创建时机
- 支持资源复用和共享

### 虚继承策略

使用虚继承支持菱形继承：
```
     GrSurfaceProxy
     ↗           ↖
GrTextureProxy  GrRenderTargetProxy
     ↖           ↗
  GrTextureRenderTargetProxy
```

避免 `GrSurfaceProxy` 基类重复。

### Unique Key 同步机制

`fSyncTargetKey` 标志控制 key 是否同步到实际纹理：
- 默认为 `true`：代理和纹理共享 key
- 设为 `false`：只在代理上保留 key（DDL 场景）

### DDL 特殊处理

`fCreatingProvider` 标记 DDL 创建的代理：
- 放松 unique key 的断言检查
- 允许代理 key 与纹理 key 不同步
- 支持跨上下文的资源共享

### 延迟上传机制

`fDeferredUploader` 支持多线程工作流：
1. 工作线程准备纹理数据（CPU 端）
2. 数据存储在上传器中
3. 代理保持未实例化
4. Flush 时实例化纹理并上传数据
5. 释放 CPU 数据

### 内存对齐警告

代码注释警告 ASAN 对齐问题：
- `std::function` 在 `GrSurfaceProxy` 中要求 16 字节对齐
- 改变字段可能触发 ASAN 警告
- 需要小心管理类布局

## 性能考量

### 延迟实例化优势

1. **内存优化**：
   - 只在需要时分配 GPU 内存
   - 避免创建永不使用的纹理
   - 支持资源预算管理

2. **资源复用**：
   - 通过 unique key 查找已存在的纹理
   - 避免重复创建相同内容的纹理

3. **DDL 支持**：
   - 在录制线程创建代理（轻量级）
   - 在 GPU 线程实例化资源（重量级）

### Mipmap 管理

- 追踪 mipmap 状态，避免不必要的重新生成
- 延迟生成 mipmap 直到实际需要
- 批量处理 mipmap 生成请求

### 内存占用估算

`onUninstantiatedGpuMemorySize()` 提供准确估算：
- 考虑 mipmap 级别
- 考虑 Exact/Approx 适配
- 用于资源预算管理

### Unique Key 查找优化

- Unique key 允许快速查找缓存的纹理
- 避免重新创建或重新上传相同内容
- 特别适合图集、字形缓存等共享资源

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrSurfaceProxy.h | 基类 | 表面代理基类 |
| src/gpu/ganesh/GrTexture.h | 代理目标 | 实际纹理资源 |
| src/gpu/ganesh/GrTextureRenderTargetProxy.h | 派生类 | 可渲染纹理代理 |
| src/gpu/ganesh/GrProxyProvider.h | 工厂 | 创建代理 |
| src/gpu/ganesh/GrResourceProvider.h | 使用 | 创建实际资源 |
| src/gpu/ganesh/GrTextureProxyPriv.h | 友元类 | 特权访问接口 |
| src/gpu/ganesh/GrTextureProxyCacheAccess.h | 友元类 | 缓存访问接口 |
| src/gpu/ganesh/GrDeferredProxyUploader.h | 使用 | 延迟上传 |
| src/gpu/ganesh/GrThreadSafeCache.h | 使用 | 线程安全缓存 |
| src/gpu/ganesh/GrSurfaceProxyView.h | 组合 | 代理视图 |
