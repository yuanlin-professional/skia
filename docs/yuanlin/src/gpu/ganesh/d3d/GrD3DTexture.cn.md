# GrD3DTexture

> 源文件
> - `src/gpu/ganesh/d3d/GrD3DTexture.h`
> - `src/gpu/ganesh/d3d/GrD3DTexture.cpp`

## 概述

`GrD3DTexture` 是 Skia 图形库中用于封装 Direct3D 12 纹理资源的核心类。它继承自 Ganesh 的通用纹理抽象 `GrTexture` 和 D3D12 特定的资源基类 `GrD3DTextureResource`,为 D3D12 后端提供完整的纹理管理功能。

该类负责管理 D3D12 纹理资源的生命周期、着色器资源视图(SRV)的创建与回收、纹理采样器状态,以及与 Skia 资源缓存系统的集成。它支持创建新纹理、封装外部纹理资源,以及创建别名纹理(aliasing textures)等多种使用场景。

## 架构位置

```
Skia GPU Backend (Ganesh)
└── Direct3D 12 后端实现
    ├── GrTexture (抽象层)
    │   └── GrD3DTexture (当前类)
    │       └── GrD3DTextureRenderTarget (派生类)
    ├── GrD3DTextureResource (资源层)
    └── GrD3DGpu (设备层)
```

该类在 Ganesh 架构中承担 D3D12 纹理的具体实现角色,桥接平台无关的 `GrTexture` 接口和平台相关的 D3D12 API。

## 主要类与结构体

### GrD3DTexture

**继承关系**
```
GrSurface (虚拟继承)
    ├── GrTexture
    │   └── GrD3DTexture
    │
    └── GrD3DTextureResource (虚拟继承)
        └── GrD3DTexture
```

该类使用虚拟继承从 `GrD3DTextureResource` 继承,以支持后续的多重继承场景。

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fShaderResourceView` | `GrD3DDescriptorHeap::CPUHandle` | 着色器资源视图句柄,用于在着色器中采样纹理 |

**内部辅助结构**

### SamplerHash

```cpp
struct SamplerHash {
    uint32_t operator()(GrSamplerState state) const;
};
```

用于采样器状态哈希计算的函数对象。D3D12 的各向异性过滤与其他过滤模式共享同一字段,因此哈希计算时 `anisoIsOrthogonal` 设为 `false`。

## 公共 API 函数

### 创建新纹理

```cpp
static sk_sp<GrD3DTexture> MakeNewTexture(
    GrD3DGpu* gpu,
    skgpu::Budgeted budgeted,
    SkISize dimensions,
    const D3D12_RESOURCE_DESC& desc,
    GrProtected isProtected,
    GrMipmapStatus mipmapStatus,
    std::string_view label);
```

创建全新的 D3D12 纹理资源。根据提供的资源描述符分配 GPU 内存并创建对应的着色器资源视图。

**初始状态**: `D3D12_RESOURCE_STATE_COPY_DEST` - 便于后续的数据上传操作

### 封装外部纹理

```cpp
static sk_sp<GrD3DTexture> MakeWrappedTexture(
    GrD3DGpu* gpu,
    SkISize dimensions,
    GrWrapCacheable cacheable,
    GrIOType ioType,
    const GrD3DTextureResourceInfo& info,
    sk_sp<GrD3DResourceState> state);
```

封装外部创建的 D3D12 纹理资源,实现跨 API 互操作。支持只读纹理和读写纹理。

**参数说明:**
- `cacheable` - 封装资源是否可被缓存
- `ioType` - I/O 类型,`kRead_GrIOType` 时纹理被标记为只读

### 创建别名纹理

```cpp
static sk_sp<GrD3DTexture> MakeAliasingTexture(
    GrD3DGpu* gpu,
    sk_sp<GrD3DTexture> originalTexture,
    const D3D12_RESOURCE_DESC& newDesc,
    D3D12_RESOURCE_STATES resourceState);
```

基于现有纹理的内存分配创建别名资源。允许在同一块 GPU 内存上创建不同格式或配置的纹理视图,实现内存重用。

**用途**: 用于瞬态资源优化,多个不同时使用的资源共享同一块内存。

### 后端纹理获取

```cpp
GrBackendTexture getBackendTexture() const override;
```

返回封装了 D3D12 特定信息的后端纹理对象,用于跨 API 边界传递纹理。

### 格式查询

```cpp
GrBackendFormat backendFormat() const override;
D3D12_CPU_DESCRIPTOR_HANDLE shaderResourceView();
```

提供纹理格式和着色器资源视图访问接口。

### 纹理参数修改

```cpp
void textureParamsModified() override {}
```

D3D12 实现中为空操作,因为采样器状态在 D3D12 中是独立管理的,不附属于纹理对象。

## 内部实现细节

### 三种构造函数

类提供三个构造函数,对应不同的创建场景:

1. **Budgeted 构造函数**: 用于 Skia 管理的新纹理,计入资源预算
2. **Wrapped 构造函数**: 用于封装外部纹理,支持缓存控制和 I/O 类型设置
3. **Protected 构造函数**: 用于内部继承(如 `GrD3DTextureRenderTarget`)

所有构造函数都必须显式调用 `GrSurface` 构造函数,因为采用了虚拟继承。

### Mipmap 状态验证

所有构造函数都包含断言验证:
```cpp
SkASSERT((GrMipmapStatus::kNotAllocated == mipmapStatus) == (1 == info.fLevelCount));
```

确保 mipmap 状态与实际层级数一致:
- `kNotAllocated` 必须对应层级数为 1
- 其他状态必须对应层级数大于 1

### 压缩纹理处理

创建新纹理时检查格式是否为压缩格式:
```cpp
if (GrDxgiFormatIsCompressed(info.fFormat)) {
    this->setReadOnly();
}
```

压缩纹理自动标记为只读,因为它们不能作为渲染目标。

### 资源状态管理

每个纹理都关联一个 `GrD3DResourceState` 对象:
- 跟踪当前的 D3D12 资源状态
- 支持并发访问的状态合并
- 用于生成必要的资源屏障(resource barriers)

### 着色器资源视图管理

着色器资源视图(SRV)的生命周期:
1. **创建**: 通过 `GrD3DResourceProvider::createShaderResourceView` 创建
2. **存储**: 保存 CPU 描述符句柄在 `fShaderResourceView`
3. **回收**: 在 `onRelease` 和 `onAbandon` 中调用 `recycleShaderView` 回收

回收机制允许描述符的重用,减少描述符堆的碎片化。

### 别名纹理实现

`MakeAliasingTexture` 的工作流程:
1. 复制原始纹理的资源信息(`fInfo`)
2. 调用内存分配器的 `createAliasingResource` 在同一内存位置创建新资源
3. 更新资源状态和描述符
4. 创建新的纹理对象共享底层内存

### 标签设置

`onSetLabel` 实现为 D3D12 资源设置调试名称:
- 添加 `_Skia_` 前缀标识
- 转换为宽字符字符串(D3D12 API 要求)
- 调用 `ID3D12Resource::SetName` 设置

这在图形调试工具(如 PIX)中非常有用。

### 后端纹理转换

`getBackendTexture` 通过 `GrBackendTextures::MakeD3D` 创建跨平台纹理对象:
- 包含纹理尺寸、格式和资源信息
- 包含当前资源状态快照
- 可以传递给其他 API 或返回给应用层

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrTexture` | 提供 Ganesh 纹理抽象基类 |
| `GrD3DTextureResource` | 提供 D3D12 资源管理基础 |
| `GrD3DGpu` | GPU 设备访问和资源提供者 |
| `GrD3DResourceState` | 资源状态跟踪 |
| `GrD3DDescriptorHeap` | 描述符句柄管理 |
| `GrD3DUtil` | D3D12 实用工具函数 |
| `GrSamplerState` | 采样器状态定义 |
| `GrD3DBackendSurfacePriv` | 后端表面转换 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrD3DTextureRenderTarget` | 多重继承的父类之一 |
| `GrD3DGpu` | 创建和管理纹理资源 |
| `GrD3DResourceProvider` | 通过工厂方法提供纹理 |
| `GrContext` | 通过 GPU 后端使用纹理 |

## 设计模式与设计决策

### 虚拟继承

从 `GrD3DTextureResource` 使用虚拟继承:
- **目的**: 支持 `GrD3DTextureRenderTarget` 的菱形继承结构
- **代价**: 额外的虚表指针和间接访问
- **收益**: 避免基类重复,保证资源管理一致性

### 工厂方法模式

三个静态工厂方法对应不同的资源来源:
- `MakeNewTexture` - 从零创建
- `MakeWrappedTexture` - 封装现有资源
- `MakeAliasingTexture` - 内存别名

每个方法封装了特定场景的复杂初始化逻辑。

### 资源句柄管理

着色器资源视图使用句柄而非直接的 COM 指针:
- 轻量级的 CPU 描述符句柄
- 便于在描述符堆中管理
- 支持描述符回收和重用

### 只读纹理优化

通过 `setReadOnly()` 标记只读纹理:
- 压缩纹理自动标记为只读
- 封装的只读纹理(`kRead_GrIOType`)也标记为只读
- 允许缓存系统做出更好的管理决策

### 资源回收机制

在 `onRelease` 和 `onAbandon` 中都回收着色器资源视图:
- `onRelease`: 正常释放路径
- `onAbandon`: 上下文丢失时的清理路径
- 确保描述符不会泄漏

### Mipmap 状态推断

对于封装纹理自动推断 mipmap 状态:
```cpp
GrMipmapStatus mipmapStatus = info.fLevelCount > 1 ? GrMipmapStatus::kValid
                                                   : GrMipmapStatus::kNotAllocated;
```

假设多层级纹理包含有效的 mipmap 数据。

## 性能考量

### 初始资源状态优化

新纹理创建时使用 `D3D12_RESOURCE_STATE_COPY_DEST`:
- 纹理创建后通常需要上传数据
- 直接设置为复制目标状态避免了额外的资源屏障
- 减少命令列表中的状态转换次数

### 描述符回收

通过 `recycleShaderView` 回收描述符:
- 减少描述符堆的分配压力
- 避免描述符堆碎片化
- 提高描述符分配效率

### 别名纹理内存优化

`MakeAliasingTexture` 实现内存重用:
- 多个瞬态资源共享同一内存池
- 减少总内存占用
- 适用于生命周期不重叠的资源

### 采样器状态哈希

`SamplerHash` 考虑了 D3D12 的特性:
- 各向异性过滤与其他过滤模式不正交(`anisoIsOrthogonal=false`)
- 所有采样器参数共同影响 `D3D12_SAMPLER_DESC::Filter` 字段
- 正确的哈希计算确保采样器缓存的准确性

### 缓存集成

根据创建方式选择不同的缓存注册:
- 新建纹理: `registerWithCache(budgeted)` - 计入预算
- 封装纹理: `registerWithCacheWrapped(cacheable)` - 可选缓存

### 虚拟继承性能影响

虚拟继承带来的开销:
- 构造时额外的虚基类初始化
- 运行时通过虚表访问基类成员
- 在纹理操作的上下文中,这些开销相对于 GPU 操作可忽略不计

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrTexture.h` | 父类 | Ganesh 纹理抽象基类 |
| `src/gpu/ganesh/d3d/GrD3DTextureResource.h` | 父类 | D3D12 纹理资源基类 |
| `src/gpu/ganesh/d3d/GrD3DTextureRenderTarget.h` | 派生类 | 纹理+渲染目标组合 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | 依赖 | GPU 设备接口 |
| `src/gpu/ganesh/d3d/GrD3DResourceState.h` | 依赖 | 资源状态管理 |
| `src/gpu/ganesh/d3d/GrD3DDescriptorHeap.h` | 依赖 | 描述符堆和句柄 |
| `src/gpu/ganesh/d3d/GrD3DUtil.h` | 依赖 | D3D12 工具函数 |
| `src/gpu/ganesh/d3d/GrD3DBackendSurfacePriv.h` | 依赖 | 后端表面转换 |
| `src/gpu/ganesh/GrSamplerState.h` | 依赖 | 采样器状态定义 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | D3D12 公共类型 |
| `include/gpu/ganesh/SkImageGanesh.h` | 依赖 | Ganesh 图像 API |
| `src/core/SkLRUCache.h` | 依赖 | LRU 缓存数据结构 |
