# GrMtlRenderTarget

> 源文件
> - `src/gpu/ganesh/mtl/GrMtlRenderTarget.h`
> - `src/gpu/ganesh/mtl/GrMtlRenderTarget.mm`

## 概述

`GrMtlRenderTarget` 是 Ganesh 图形后端中 Metal 实现的渲染目标类,表示可以作为渲染操作输出的 Metal 纹理表面。该类封装了 Metal 的颜色附件和可选的 resolve 附件,支持单采样和多重采样抗锯齿(MSAA)渲染目标。作为 `GrRenderTarget` 的具体实现,它管理着渲染所需的颜色缓冲区、MSAA 缓冲区以及帧缓冲对象的缓存,为 Metal 渲染管线提供目标表面。

## 架构位置

`GrMtlRenderTarget` 位于 Skia 图形库的 GPU 后端渲染目标层次结构中:

```
Skia 图形库
└── GPU 后端 (src/gpu)
    └── Ganesh 渲染引擎 (ganesh)
        ├── GrSurface (表面基类)
        │   └── GrRenderTarget (渲染目标抽象基类)
        │       └── GrMtlRenderTarget (Metal 渲染目标) ← 当前类
        └── Metal 后端实现 (mtl)
            ├── GrMtlAttachment (附件表示)
            ├── GrMtlFramebuffer (帧缓冲对象)
            └── GrMtlGpu (GPU 接口)
```

该类与 Metal 纹理附件和帧缓冲对象紧密协作,为渲染操作提供输出目标。

## 主要类与结构体

### GrMtlRenderTarget 类

Metal 渲染目标的具体实现类。

**继承关系:**
- 继承: `GrRenderTarget` (渲染目标抽象类)
- 间接继承: `GrSurface` (表面基类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorAttachment` | `sk_sp<GrMtlAttachment>` | 颜色附件,存储渲染输出 |
| `fResolveAttachment` | `sk_sp<GrMtlAttachment>` | Resolve 附件,用于 MSAA resolve |
| `fCachedFramebuffers` | `sk_sp<const GrMtlFramebuffer>[4]` | 缓存的帧缓冲对象数组 |

### Wrapped 枚举

用于构造函数重载的标记类型。

```cpp
enum Wrapped { kWrapped };
```

## 公共 API 函数

### 工厂方法

```cpp
static sk_sp<GrMtlRenderTarget> MakeWrappedRenderTarget(
    GrMtlGpu* gpu,
    SkISize dimensions,
    int sampleCnt,
    id<MTLTexture> texture)
```
从现有 Metal 纹理创建包装的渲染目标。如果采样数大于 1 且纹理是单采样的,会自动创建 MSAA 纹理并使用传入纹理作为 resolve 目标。

### 附件访问

```cpp
GrMtlAttachment* colorAttachment() const
```
返回颜色附件指针。

```cpp
id<MTLTexture> colorMTLTexture() const
```
返回颜色附件的 Metal 纹理对象。

```cpp
GrMtlAttachment* resolveAttachment() const
```
返回 resolve 附件指针(MSAA 情况下使用)。

```cpp
id<MTLTexture> resolveMTLTexture() const
```
返回 resolve 附件的 Metal 纹理对象。

```cpp
GrMtlAttachment* nonMSAAAttachment() const
```
返回非 MSAA 附件。如果颜色附件是单采样则返回颜色附件,否则返回 resolve 附件。

### 帧缓冲管理

```cpp
const GrMtlFramebuffer* getFramebuffer(bool withResolve, bool withStencil)
```
获取或创建具有指定特性的帧缓冲对象。根据是否需要 resolve 和模板附件,返回对应的缓存帧缓冲。

### 后端接口

```cpp
GrBackendRenderTarget getBackendRenderTarget() const override
```
返回后端渲染目标表示,用于跨 API 互操作。

```cpp
GrBackendFormat backendFormat() const override
```
返回后端格式信息。

```cpp
bool canAttemptStencilAttachment(bool useMSAASurface) const override
```
检查是否可以附加模板缓冲。Metal 实现始终返回 `true`。

## 内部实现细节

### 构造函数设计

类提供两个私有/保护的构造函数:

1. **包装构造函数** (带 `Wrapped` 标记):
   - 用于包装外部 Metal 纹理
   - 调用 `registerWithCacheWrapped(kNo)` 标记为不可缓存

2. **子类构造函数**:
   - 供子类(如 `GrMtlTextureRenderTarget`)使用
   - 不注册到缓存,由子类控制

### MSAA 处理逻辑

`MakeWrappedRenderTarget()` 实现了灵活的 MSAA 处理:

```cpp
if (sampleCnt > 1) {
    if ([texture sampleCount] == 1) {
        // 创建 MSAA 纹理,使用原纹理作为 resolve 目标
        sk_sp<GrAttachment> msaaAttachment =
            rp->makeMSAAAttachment(...);
        // colorAttachment = msaa, resolveAttachment = texture
    } else {
        // 纹理本身就是 MSAA,无需 resolve
        // colorAttachment = texture, resolveAttachment = nil
    }
}
```

这种设计支持两种 MSAA 场景:
- **自动 resolve**: 内部 MSAA + 外部单采样纹理
- **显式 MSAA**: 纹理本身为 MSAA

### 帧缓冲缓存策略

帧缓冲对象按两个布尔标志缓存,共 4 种组合:

```cpp
static int renderpass_features_to_index(bool hasResolve, bool hasStencil) {
    int index = 0;
    if (hasResolve) index += 1;
    if (hasStencil) index += 2;
    return index;
}
```

缓存索引映射:
- `[0]`: 无 resolve,无模板
- `[1]`: 有 resolve,无模板
- `[2]`: 无 resolve,有模板
- `[3]`: 有 resolve,有模板

### 资源释放机制

实现了两种资源释放路径:

1. **`onRelease()`**: 正常释放,清理附件引用
2. **`onAbandon()`**: 放弃资源,GPU 上下文丢失时调用

两者都将附件设置为 `nil`,依赖智能指针自动释放底层 Metal 对象。

### 标签设置

`onSetLabel()` 为调试提供友好的纹理标签:

```cpp
// MSAA 场景
colorAttachment.label = "_Skia_MSAA_<label>"
resolveAttachment.label = "_Skia_Resolve_<label>"

// 单采样场景
colorAttachment.label = "_Skia_<label>"
```

### 内存计算

```cpp
size_t onGpuMemorySize() const override { return 0; }
```

返回 0 因为内存由附件对象管理,避免重复计算。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrRenderTarget` | 渲染目标抽象基类 |
| `GrSurface` | 表面基类 |
| `GrMtlAttachment` | Metal 附件表示 |
| `GrMtlFramebuffer` | 帧缓冲对象 |
| `GrMtlGpu` | Metal GPU 接口 |
| `GrResourceProvider` | 资源提供者,创建 MSAA 附件 |
| `GrBackendSurface` | 后端表面表示 |
| `Metal.framework` | Metal API |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `GrMtlTextureRenderTarget` | 继承 `GrMtlRenderTarget`,实现纹理+渲染目标 |
| `GrMtlOpsRenderPass` | 使用渲染目标执行渲染操作 |
| `GrMtlGpu` | 创建和管理渲染目标 |

## 设计模式与设计决策

### 1. 组合模式 (Composition)

渲染目标通过组合 `GrMtlAttachment` 对象构建,而不是直接持有 Metal 纹理:

```cpp
sk_sp<GrMtlAttachment> fColorAttachment;
sk_sp<GrMtlAttachment> fResolveAttachment;
```

这种设计实现了附件的独立管理和复用。

### 2. 懒加载缓存 (Lazy Cache)

帧缓冲对象仅在首次请求时创建:

```cpp
if (fCachedFramebuffers[cacheIndex]) {
    return fCachedFramebuffers[cacheIndex].get();
}
// 创建并缓存
fCachedFramebuffers[cacheIndex] = GrMtlFramebuffer::Make(...);
```

### 3. 工厂模式 (Factory Pattern)

静态工厂方法 `MakeWrappedRenderTarget()` 封装复杂的创建逻辑,包括 MSAA 纹理的自动创建。

### 4. 智能指针管理

使用 `sk_sp` 智能指针管理附件生命周期:

```cpp
sk_sp<GrMtlAttachment> fColorAttachment;
```

自动处理引用计数和资源释放。

### 5. 策略模式 (Strategy)

通过参数控制帧缓冲特性(withResolve, withStencil),支持不同的渲染策略。

### 6. 适配器模式 (Adapter)

`getBackendRenderTarget()` 将内部表示转换为跨平台的 `GrBackendRenderTarget`,用于与其他 API 互操作。

### 7. 模板方法模式 (Template Method)

实现基类的虚函数 `onRelease()`, `onAbandon()`, `onSetLabel()` 等,定义特定于 Metal 的行为。

## 性能考量

### 1. 帧缓冲缓存

缓存 4 种帧缓冲配置避免重复创建,减少 Metal 对象分配开销。每种配置仅创建一次,后续直接复用。

### 2. 智能 MSAA 管理

- **自动检测**: 根据纹理采样数自动决定是否创建额外 MSAA 缓冲
- **按需 resolve**: 仅在需要时附加 resolve 附件
- **手动 resolve 标记**: `setRequiresManualMSAAResolve()` 优化 resolve 时机

### 3. 内存零开销标识

`onGpuMemorySize()` 返回 0 避免与附件对象的内存重复计算,保证统计准确性。

### 4. 附件共享

通过智能指针允许附件在多个渲染目标间共享,减少内存占用。

### 5. ARC 内存管理

```cpp
#if !__has_feature(objc_arc)
#error This file must be compiled with Arc.
```

强制使用 ARC 自动管理 Metal 对象,避免内存泄漏。

### 6. 格式验证

创建时验证纹理用途标志:

```cpp
SkASSERT(MTLTextureUsageRenderTarget & texture.usage);
```

确保纹理可用作渲染目标,避免运行时错误。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrRenderTarget.h` | 继承关系 | 渲染目标抽象基类 |
| `src/gpu/ganesh/GrSurface.h` | 继承关系 | 表面基类 |
| `src/gpu/ganesh/mtl/GrMtlAttachment.h/mm` | 组合关系 | 附件对象 |
| `src/gpu/ganesh/mtl/GrMtlFramebuffer.h/mm` | 使用关系 | 帧缓冲对象 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` | 使用关系 | GPU 接口 |
| `src/gpu/ganesh/mtl/GrMtlTextureRenderTarget.h/mm` | 继承关系 | 纹理+渲染目标子类 |
| `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.h/mm` | 使用关系 | 渲染通道使用渲染目标 |
| `src/gpu/ganesh/GrResourceProvider.h` | 使用关系 | 创建 MSAA 附件 |
| `include/gpu/ganesh/GrBackendSurface.h` | 使用关系 | 后端表面表示 |
| `include/gpu/ganesh/mtl/GrMtlBackendSurface.h` | 使用关系 | Metal 后端表面工具 |
