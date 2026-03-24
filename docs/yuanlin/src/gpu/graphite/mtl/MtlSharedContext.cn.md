# MtlSharedContext -- Metal 共享上下文

> 源文件:
> - `src/gpu/graphite/mtl/MtlSharedContext.h`
> - `src/gpu/graphite/mtl/MtlSharedContext.mm`

## 概述

MtlSharedContext 是 Graphite Metal 后端的共享上下文实现,继承自 `SharedContext` 基类。它持有 Metal 设备、内存分配器、能力对象以及预创建的深度模板状态缓存,为所有 Recorder 和 ResourceProvider 提供共享的后端资源。

## 架构位置

```
SharedContext (抽象基类)
  -> MtlSharedContext  <-- 本模块
       -> id<MTLDevice> (Metal 设备)
       -> MtlCaps (能力查询)
       -> MtlMemoryAllocator (内存分配器)
       -> MtlThreadSafeResourceProvider (线程安全资源提供者)
```

## 主要类与结构体

### MtlThreadSafeResourceProvider

```cpp
class MtlThreadSafeResourceProvider final : public ThreadSafeResourceProvider {
public:
    MtlThreadSafeResourceProvider(std::unique_ptr<ResourceProvider>);
};
```
Metal 特化的线程安全资源提供者,仅是对基类的简单包装。

### MtlSharedContext

```cpp
class MtlSharedContext final : public SharedContext {
    sk_sp<skgpu::MtlMemoryAllocator> fMemoryAllocator;
    sk_cfp<id<MTLDevice>> fDevice;
    THashMap<DepthStencilSettings, sk_cfp<id<MTLDepthStencilState>>> fDepthStencilStates;
};
```

## 公共 API 函数

### Make -- 工厂方法
```cpp
static sk_sp<SharedContext> Make(const MtlBackendContext&, const ContextOptions&);
```
验证 OS 最低版本(macOS 10.15 / iOS 13),创建 MtlCaps 和内存分配器,初始化共享上下文。

### 访问器
```cpp
id<MTLDevice> device() const;
const MtlCaps& mtlCaps() const;
skgpu::MtlMemoryAllocator* memoryAllocator() const;
MtlThreadSafeResourceProvider* threadSafeResourceProvider() const;
```

### getCompatibleDepthStencilState
```cpp
sk_cfp<id<MTLDepthStencilState>> getCompatibleDepthStencilState(const DepthStencilSettings&) const;
```
从预创建的缓存中查找匹配的 `MTLDepthStencilState`。

## 内部实现细节

### 深度模板状态预创建

构造函数中预创建 Graphite 常用的所有深度模板状态:
- `kDirectDepthLessPass` / `kDirectDepthLEqualPass`
- `kWindingStencilPass` / `kEvenOddStencilPass`
- `kRegularCoverPass` / `kInverseCoverPass`
- 忽略深度模板的默认状态

使用 `THashMap` 存储,运行时查找无需加锁（只读访问）。

### 比较和模板操作映射

```cpp
MTLCompareFunction compare_op_to_mtl(CompareOp op);
MTLStencilOperation stencil_op_to_mtl(StencilOp op);
MTLStencilDescriptor* stencil_face_to_mtl(DepthStencilSettings::Face face);
```

### 管线创建委托

```cpp
sk_sp<GraphicsPipeline> createGraphicsPipeline(...) override;
```
直接委托给 `MtlGraphicsPipeline::Make`。

## 依赖关系

- `SharedContext` -- 基类
- `MtlCaps` -- Metal 能力
- `MtlMemoryAllocatorImpl` -- 内存分配
- `MtlResourceProvider` -- 资源提供
- `CommonDepthStencilSettings.h` -- 预定义的深度模板设置

## 设计模式与设计决策

1. **深度模板状态预创建**: 因为 Graphite 的深度模板组合非常有限（7 种），在构造时全部预创建并缓存,避免运行时锁竞争。
2. **最低版本检查**: 在工厂方法中早期失败，提供清晰的错误消息。
3. **资源清理顺序**: 析构时先重置线程安全资源提供者,再清理全局缓存,确保资源在分配器销毁前释放。

## 性能考量

- 深度模板状态查找为 O(1) 哈希表查找,无同步开销。
- `MTLDepthStencilState` 创建是一次性开销,运行时完全消除。
- 内存分配器通过 `MtlMemoryAllocatorImpl` 管理,支持子分配优化。

## 相关文件

- `src/gpu/graphite/SharedContext.h` -- 共享上下文基类
- `src/gpu/graphite/mtl/MtlCaps.h` -- Metal 能力
- `src/gpu/graphite/mtl/MtlResourceProvider.h` -- 资源提供者
- `src/gpu/graphite/render/CommonDepthStencilSettings.h` -- 通用深度模板设置
