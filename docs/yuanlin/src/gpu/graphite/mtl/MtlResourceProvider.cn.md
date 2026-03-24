# MtlResourceProvider -- Metal 资源提供者

> 源文件:
> - `src/gpu/graphite/mtl/MtlResourceProvider.h`
> - `src/gpu/graphite/mtl/MtlResourceProvider.mm`

## 概述

MtlResourceProvider 是 Graphite Metal 后端的资源提供者实现,继承自 `ResourceProvider` 基类。它负责创建 Metal 特定的 GPU 资源,包括纹理、缓冲区、采样器、计算管线和 MSAA 加载管线。每个 Recorder 拥有独立的 ResourceProvider 实例。

## 架构位置

```
ResourceProvider (抽象基类)
  -> MtlResourceProvider  <-- 本模块
       -> MtlTexture / MtlBuffer / MtlSampler (Metal 资源)
       -> MtlGraphicsPipeline / MtlComputePipeline (Metal 管线)
```

## 主要类与结构体

### MtlResourceProvider

```cpp
class MtlResourceProvider final : public ResourceProvider {
    THashMap<uint32_t, sk_sp<MtlGraphicsPipeline>> fLoadMSAAPipelines;
};
```

`fLoadMSAAPipelines` 以渲染通道键为索引缓存 MSAA 加载管线。

## 公共 API 函数

### findOrCreateLoadMSAAPipeline
```cpp
sk_sp<MtlGraphicsPipeline> findOrCreateLoadMSAAPipeline(const RenderPassDesc&);
```
查找或创建用于从 resolve 纹理加载 MSAA 数据的专用管线。以渲染通道描述的哈希键做缓存查找。

## 内部实现细节

### 资源创建方法

| 方法 | 委托目标 |
|------|----------|
| `createTexture` | `MtlTexture::Make` |
| `onCreateWrappedTexture` | `MtlTexture::MakeWrapped` |
| `createBuffer` | `MtlBuffer::Make` |
| `createSampler` | `MtlSampler::Make` |
| `createComputePipeline` | `MtlComputePipeline::Make` |
| `onCreateBackendTexture` | `MtlTexture::MakeMtlTexture` + `BackendTextures::MakeMetal` |
| `onDeleteBackendTexture` | `SkCFSafeRelease` |

### 包装纹理

`onCreateWrappedTexture` 从 `BackendTexture` 提取 `CFTypeRef` 句柄,通过 `sk_ret_cfp` 增加引用计数后传给 `MtlTexture::MakeWrapped`。

### MtlThreadSafeResourceProvider

```cpp
MtlThreadSafeResourceProvider::MtlThreadSafeResourceProvider(
    std::unique_ptr<ResourceProvider> resourceProvider)
    : ThreadSafeResourceProvider(std::move(resourceProvider)) {}
```
简单转发构造,无额外逻辑。

## 依赖关系

- `ResourceProvider` -- 基类
- `MtlTexture` / `MtlBuffer` / `MtlSampler` -- Metal 资源类型
- `MtlGraphicsPipeline` / `MtlComputePipeline` -- Metal 管线
- `MtlSharedContext` -- 共享上下文
- `MtlCaps` -- 能力查询

## 设计模式与设计决策

1. **工厂方法委托**: 每种资源类型的创建直接委托给对应 Metal 类的静态工厂方法。
2. **MSAA 管线缓存**: 使用渲染通道键的哈希映射缓存,避免为相同渲染通道配置重复创建管线。
3. **Backend 纹理生命周期**: 创建时返回原始 `CFTypeRef`(需手动释放),删除时通过 `SkCFSafeRelease` 释放。

## 性能考量

- MSAA 加载管线在首次需要时惰性创建并缓存。
- 每个 Recorder 独立的 ResourceProvider 避免了资源管理的锁竞争。

## 相关文件

- `src/gpu/graphite/ResourceProvider.h` -- 基类
- `src/gpu/graphite/mtl/MtlTexture.h` -- Metal 纹理
- `src/gpu/graphite/mtl/MtlBuffer.h` -- Metal 缓冲区
- `src/gpu/graphite/mtl/MtlSampler.h` -- Metal 采样器
- `src/gpu/graphite/mtl/MtlGraphicsPipeline.h` -- Metal 图形管线
