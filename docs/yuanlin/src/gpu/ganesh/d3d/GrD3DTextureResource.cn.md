# GrD3DTextureResource

> 源文件
> - `src/gpu/ganesh/d3d/GrD3DTextureResource.h`
> - `src/gpu/ganesh/d3d/GrD3DTextureResource.cpp`

## 概述

`GrD3DTextureResource` 是 Direct3D 12 后端中纹理资源管理的基础类。它封装了 D3D12 纹理资源(`ID3D12Resource`)及其关联的内存分配、资源状态跟踪和生命周期管理。该类提供了纹理资源的创建、状态转换、MSAA 表面生成等核心功能,是所有 D3D12 纹理类型的公共基础。

该类采用非拷贝(`SkNoncopyable`)设计,确保资源的唯一所有权。它通过内部的 `Resource` 类实现引用计数的资源管理,并与 Skia 的释放回调机制集成,支持外部资源的生命周期通知。

## 架构位置

```
Skia GPU Backend (Ganesh)
└── Direct3D 12 资源层
    ├── GrD3DTextureResource (当前类 - 基础资源管理)
    │   ├── GrD3DTexture (纹理)
    │   ├── GrD3DRenderTarget (渲染目标)
    │   └── GrD3DTextureRenderTarget (纹理+渲染目标)
    ├── GrD3DResourceState (状态跟踪)
    └── GrD3DAlloc (内存分配)
```

该类是 D3D12 纹理类型层次结构的根基,为纹理、渲染目标及其组合提供共享的资源管理功能。

## 主要类与结构体

### GrD3DTextureResource

**继承关系**
- 继承自: `SkNoncopyable` - 禁止拷贝操作
- 特性: 被 `GrD3DTexture` 和 `GrD3DRenderTarget` 虚拟继承

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInfo` | `GrD3DTextureResourceInfo` | 纹理资源完整信息(资源、格式、层级数等) |
| `fState` | `sk_sp<GrD3DResourceState>` | 资源状态跟踪对象 |
| `fResource` | `sk_sp<Resource>` | 内部资源封装,支持引用计数和释放回调 |

### Resource 内部类

```cpp
class Resource : public GrTextureResource
```

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fResource` | `gr_cp<ID3D12Resource>` | D3D12 纹理资源的 COM 智能指针 |
| `fAlloc` | `sk_sp<GrD3DAlloc>` | 关联的内存分配对象 |

该类继承自 `GrTextureResource`,提供引用计数和释放回调机制。

## 公共 API 函数

### 资源访问器

```cpp
ID3D12Resource* d3dResource() const;
```
获取底层的 D3D12 资源对象指针,用于 D3D12 API 调用。

```cpp
DXGI_FORMAT dxgiFormat() const;
```
返回纹理的 DXGI 格式枚举值。

```cpp
GrBackendFormat getBackendFormat() const;
```
返回 Skia 统一的后端格式表示。

```cpp
sk_sp<Resource> resource() const;
```
获取内部资源对象的智能指针,用于引用计数管理。

```cpp
uint32_t mipLevels() const;
```
返回纹理的 mipmap 层级数量。

### 资源状态管理

```cpp
sk_sp<GrD3DResourceState> grD3DResourceState() const;
```
获取资源状态跟踪对象。

```cpp
D3D12_RESOURCE_STATES currentState() const;
```
返回当前的 D3D12 资源状态标志位。

```cpp
void setResourceState(const GrD3DGpu* gpu,
                     D3D12_RESOURCE_STATES newResourceState,
                     unsigned int subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES);
```
设置资源状态并添加必要的资源屏障到 GPU 命令队列。

```cpp
void updateResourceState(D3D12_RESOURCE_STATES newState);
```
直接更新状态跟踪,不生成 GPU 命令。用于隐式状态转换(如某些 GPU 命令的副作用)。

```cpp
void prepareForPresent(GrD3DGpu* gpu);
```
将资源转换为 `D3D12_RESOURCE_STATE_PRESENT` 状态,准备呈现到屏幕。

### 采样质量查询

```cpp
unsigned int sampleQualityPattern() const;
```
返回多重采样的质量模式。

### 静态资源创建函数

```cpp
static bool InitTextureResourceInfo(
    GrD3DGpu* gpu,
    const D3D12_RESOURCE_DESC& desc,
    D3D12_RESOURCE_STATES initialState,
    GrProtected isProtected,
    D3D12_CLEAR_VALUE* clearValue,
    GrD3DTextureResourceInfo* info);
```
初始化纹理资源信息结构体,分配 GPU 内存并创建 D3D12 资源对象。

```cpp
static std::pair<GrD3DTextureResourceInfo, sk_sp<GrD3DResourceState>> CreateMSAA(
    GrD3DGpu* gpu,
    SkISize dimensions,
    int sampleCnt,
    const GrD3DTextureResourceInfo& info,
    SkColor4f clearColor);
```
创建 MSAA 表面资源,返回资源信息和状态对象对。

### 释放回调管理

```cpp
void setResourceRelease(sk_sp<GrSurface::RefCntedReleaseProc> releaseHelper);
```
设置资源释放回调,当 GPU 完成对资源的所有工作后调用。

## 内部实现细节

### 资源状态转换机制

`setResourceState` 实现了 D3D12 资源屏障的自动管理:

1. **状态检查**: 如果新状态与当前状态相同,直接返回避免不必要的屏障
2. **屏障构造**: 创建 `D3D12_RESOURCE_TRANSITION_BARRIER` 描述状态转换
3. **屏障提交**: 通过 `gpu->addResourceBarriers` 添加到命令队列
4. **状态更新**: 更新本地状态跟踪

支持子资源级别的状态转换,默认应用于所有子资源。

### 纹理资源初始化流程

`InitTextureResourceInfo` 的执行步骤:

1. **尺寸验证**: 检查宽度和高度非零
2. **保护内存检查**: 当前不支持保护内存,直接返回失败
3. **Mip 层级验证**: 确保 `MipLevels > 0`,不支持自动计算
4. **内存分配**: 通过内存分配器在默认堆上创建资源
5. **信息填充**: 设置格式、层级数、采样数等元数据

### MSAA 表面创建

`CreateMSAA` 创建专用的多重采样表面:

**资源描述符配置:**
- 维度: 2D 纹理
- 对齐: 0 (使用默认 64KB 对齐)
- Mip 层级: 固定为 1 (MSAA 表面不支持 mipmap)
- 采样质量: `DXGI_STANDARD_MULTISAMPLE_QUALITY_PATTERN`
- 标志: `D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET`

**初始状态**: `D3D12_RESOURCE_STATE_RENDER_TARGET`

**清除值**: 根据提供的 `clearColor` 设置,用于优化清除操作。

### 资源释放流程

`releaseResource` 实现了资源的完全释放:
1. 重置 `fResource` 智能指针(触发 `Resource::freeGPUData`)
2. 重置 `fInfo.fResource` COM 指针
3. 重置 `fInfo.fAlloc` 内存分配对象

析构函数验证资源已被释放,确保没有资源泄漏。

### Resource 类的 GPU 数据释放

`Resource::freeGPUData` 在引用计数归零时调用:
1. 调用释放回调(`invokeReleaseProc`) - 通知外部资源可用
2. 释放 D3D12 资源引用
3. 释放内存分配对象

这确保了释放回调在 GPU 完成所有工作后才触发。

### 呈现准备

`prepareForPresent` 是 `setResourceState` 的便捷包装:
- 转换到 `D3D12_RESOURCE_STATE_PRESENT` 状态
- 允许资源被交换链呈现
- 通常用于后缓冲区或窗口表面

### 友元类设计

`GrD3DRenderTarget` 声明为友元类:
- 允许渲染目标访问纹理资源的内部实现
- 支持纹理和渲染目标的紧密集成
- 避免了不必要的公共接口暴露

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrD3DResourceState` | 资源状态跟踪和合并 |
| `GrD3DAlloc` | GPU 内存分配管理 |
| `GrD3DGpu` | GPU 设备和命令队列访问 |
| `GrD3DAMDMemoryAllocator` | 内存分配器实现 |
| `GrTextureResource` | 通用纹理资源基类 |
| `GrD3DTypes` | D3D12 类型定义 |
| `GrD3DBackendSurface` | 后端表面定义 |
| `GrTypesPriv` | Ganesh 内部类型 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrD3DTexture` | 虚拟继承此类作为纹理基础 |
| `GrD3DRenderTarget` | 虚拟继承此类作为渲染目标基础 |
| `GrD3DTextureRenderTarget` | 通过父类间接继承 |
| `GrD3DGpu` | 调用资源创建和管理方法 |

## 设计模式与设计决策

### 非拷贝语义

继承 `SkNoncopyable` 明确禁止拷贝:
- GPU 资源是昂贵的,不应隐式拷贝
- 强制使用智能指针进行所有权传递
- 避免意外的资源复制

### 内部 Resource 类封装

使用嵌套的 `Resource` 类而非直接管理资源:
- **分离关注点**: `Resource` 专注于引用计数和释放
- **释放回调支持**: 继承 `GrTextureResource` 获得回调机制
- **延迟释放**: 资源在最后一个引用消失时自动清理

### 虚拟继承准备

该类被设计为虚拟继承使用:
- 支持菱形继承(在 `GrD3DTextureRenderTarget` 中)
- 避免资源信息重复
- 保证单一的资源状态跟踪

### 状态转换分离

提供两种状态更新方法:
1. **`setResourceState`**: 生成资源屏障,用于显式状态转换
2. **`updateResourceState`**: 仅更新跟踪,用于隐式状态转换

这种分离允许正确处理 D3D12 的隐式状态提升和衰减。

### 静态工厂方法

`InitTextureResourceInfo` 和 `CreateMSAA` 作为静态方法:
- 不依赖对象实例
- 可以在对象构造前使用
- 支持资源预分配和验证

### 友元访问模式

将 `GrD3DRenderTarget` 声明为友元:
- 避免暴露过多内部细节
- 允许紧密集成的类访问必要的实现
- 保持接口的简洁性

## 性能考量

### 资源屏障优化

`setResourceState` 中的状态比较:
```cpp
if (newResourceState == currentResourceState) {
    return;
}
```
避免不必要的资源屏障,减少命令列表开销和 GPU 同步点。

### 默认对齐

MSAA 表面使用默认对齐(`Alignment = 0`):
- D3D12 自动选择 64KB 对齐
- 适合大多数纹理资源
- 减少内存碎片

### 清除值优化

在资源创建时提供 `D3D12_CLEAR_VALUE`:
- 允许驱动程序优化清除操作
- 可能启用压缩清除(fast clear)
- 对于渲染目标特别重要

### 子资源状态管理

默认应用状态转换到所有子资源:
- 简化了常见情况的处理
- 支持细粒度的子资源状态(通过 `subresource` 参数)
- 在需要时可以单独转换 mipmap 层级

### MSAA 质量模式

使用标准质量模式:
```cpp
msTextureDesc.SampleDesc.Quality = DXGI_STANDARD_MULTISAMPLE_QUALITY_PATTERN;
```
保证跨硬件的兼容性,而非追求最高质量。

### 内存分配策略

使用 `D3D12_HEAP_TYPE_DEFAULT`:
- 资源位于 GPU 专用内存
- 最佳的渲染和采样性能
- CPU 不可直接访问,需通过复制操作

### 延迟资源释放

通过 `Resource` 类的引用计数:
- 资源可以在 GPU 对象之间安全共享
- 仅在最后一个引用消失时释放
- 支持复杂的资源生命周期管理

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DTexture.h` | 派生类 | D3D12 纹理实现 |
| `src/gpu/ganesh/d3d/GrD3DRenderTarget.h` | 派生类 | D3D12 渲染目标实现 |
| `src/gpu/ganesh/d3d/GrD3DTextureRenderTarget.h` | 派生类 | 组合纹理+渲染目标 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | 依赖 | GPU 设备和命令队列 |
| `src/gpu/ganesh/d3d/GrD3DResourceState.h` | 依赖 | 资源状态跟踪 |
| `src/gpu/ganesh/d3d/GrD3DAMDMemoryAllocator.h` | 依赖 | 内存分配器 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | D3D12 类型定义 |
| `include/gpu/ganesh/d3d/GrD3DBackendSurface.h` | 依赖 | 后端表面定义 |
| `include/gpu/ganesh/GrBackendSurface.h` | 依赖 | 跨后端表面抽象 |
| `src/gpu/ganesh/GrManagedResource.h` | 相关 | 托管资源基类 |
| `src/gpu/ganesh/GrGpuResourcePriv.h` | 依赖 | GPU 资源私有接口 |
| `include/core/SkTypes.h` | 依赖 | Skia 核心类型 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | Ganesh 私有类型 |
