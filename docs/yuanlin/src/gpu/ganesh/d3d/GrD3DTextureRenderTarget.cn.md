# GrD3DTextureRenderTarget

> 源文件
> - `src/gpu/ganesh/d3d/GrD3DTextureRenderTarget.h`
> - `src/gpu/ganesh/d3d/GrD3DTextureRenderTarget.cpp`

## 概述

`GrD3DTextureRenderTarget` 是一个多重继承类,同时实现了纹理和渲染目标功能。它允许同一个 D3D12 资源既可以作为纹理进行采样,又可以作为渲染目标进行绘制。这种双重用途的资源在 GPU 渲染管线中非常常见,例如用于实现渲染到纹理(Render-to-Texture)、后处理效果和多遍渲染等场景。

该类处理了 MSAA(多重采样抗锯齿)和非 MSAA 两种配置,并支持创建新资源或封装外部 D3D12 资源。对于 MSAA 情况,它管理额外的 MSAA 表面和解析目标。

## 架构位置

```
Skia GPU Backend (Ganesh)
└── Direct3D 12 实现
    ├── GrD3DGpu               # GPU 设备管理
    ├── GrD3DTextureResource   # 纹理资源基类
    ├── GrD3DTexture           # 纹理实现
    ├── GrD3DRenderTarget      # 渲染目标实现
    └── GrD3DTextureRenderTarget  # 组合纹理+渲染目标 (当前类)
```

该类位于 Ganesh D3D12 后端的资源层级顶端,组合了纹理和渲染目标的功能。

## 主要类与结构体

### GrD3DTextureRenderTarget

**继承关系**
```
GrSurface (虚拟继承)
    ├── GrTexture
    │   └── GrD3DTexture ─────┐
    │                          ├─→ GrD3DTextureRenderTarget
    └── GrRenderTarget         │
        └── GrD3DRenderTarget ─┘
```

该类使用多重继承同时继承 `GrD3DTexture` 和 `GrD3DRenderTarget`,并通过虚拟继承共享 `GrSurface` 基类。

**关键成员变量**

该类不引入新的成员变量,所有数据继承自两个父类:
- 从 `GrD3DTexture` 继承纹理相关的资源和着色器资源视图
- 从 `GrD3DRenderTarget` 继承渲染目标视图和 MSAA 配置

## 公共 API 函数

### 创建新资源

```cpp
static sk_sp<GrD3DTextureRenderTarget> MakeNewTextureRenderTarget(
    GrD3DGpu* gpu,
    skgpu::Budgeted budgeted,
    SkISize dimensions,
    int sampleCnt,
    const D3D12_RESOURCE_DESC& resourceDesc,
    GrProtected isProtected,
    GrMipmapStatus mipmapStatus,
    std::string_view label);
```

创建全新的纹理渲染目标资源。自动创建所需的 D3D12 资源、着色器资源视图和渲染目标视图。

**参数说明:**
- `budgeted` - 资源是否计入 GPU 预算管理
- `sampleCnt` - 采样数量,大于 1 时启用 MSAA
- `resourceDesc` - D3D12 资源描述符
- `mipmapStatus` - Mipmap 状态(已分配、脏数据或未分配)

### 封装外部资源

```cpp
static sk_sp<GrD3DTextureRenderTarget> MakeWrappedTextureRenderTarget(
    GrD3DGpu* gpu,
    SkISize dimensions,
    int sampleCnt,
    GrWrapCacheable cacheable,
    const GrD3DTextureResourceInfo& info,
    sk_sp<GrD3DResourceState> state);
```

封装外部创建的 D3D12 资源,使其可在 Skia 渲染管线中使用。支持跨 API 互操作场景。

### 格式查询

```cpp
GrBackendFormat backendFormat() const override;
```

返回后端特定的纹理格式信息,通过调用继承的 `getBackendFormat()` 实现。

## 内部实现细节

### 四种构造函数

类提供四个私有构造函数,覆盖所有使用场景:

1. **MSAA + 非封装**: 创建新的 MSAA 纹理渲染目标
2. **非 MSAA + 非封装**: 创建新的普通纹理渲染目标
3. **MSAA + 封装**: 封装外部 MSAA 纹理渲染目标
4. **非 MSAA + 封装**: 封装外部普通纹理渲染目标

### MSAA 资源管理

对于 MSAA 纹理渲染目标:
- **主资源** (`info`): 用于纹理采样的解析目标
- **MSAA 资源** (`msaaInfo`): 实际的多重采样渲染表面
- **两个渲染目标视图**:
  - `colorRenderTargetView`: 指向 MSAA 表面(实际绘制目标)
  - `resolveRenderTargetView`: 指向解析目标(纹理采样源)

### 初始资源状态

根据是否使用 MSAA 设置不同的初始状态:
- **MSAA**: `D3D12_RESOURCE_STATE_RESOLVE_DEST` - 为解析操作做准备
- **非 MSAA**: `D3D12_RESOURCE_STATE_RENDER_TARGET` - 直接用于渲染

### Clear Value 优化

在创建新资源时设置 `D3D12_CLEAR_VALUE`:
- **新建 MSAA 表面**: 清除为透明黑色 `(0,0,0,0)` - 适用于蒙版
- **封装 MSAA 表面**: 清除为不透明白色 `(1,1,1,1)` - 一般用途
- 设置 clear value 可让 D3D12 驱动优化清除操作

### 资源释放顺序

在 `onAbandon` 和 `onRelease` 中特别注意调用顺序:
```cpp
GrD3DTexture::onAbandon();      // 先调用纹理的释放
GrD3DRenderTarget::onAbandon(); // 后调用渲染目标的释放
```

这个顺序确保纹理的空闲回调(idle procs)被正确处理。

### GPU 内存计算

`onGpuMemorySize` 计算考虑了 MSAA 的额外内存开销:
- MSAA 情况: 计入多重采样表面和解析表面,样本数 +1
- 包含所有 mipmap 层级的内存占用

### Windows 编译器警告处理

使用 `#pragma warning` 抑制多重继承的菱形继承警告:
```cpp
#pragma warning(disable: 4250)  // 禁用支配继承警告
```

这是因为 `asTexture` 和 `asRenderTarget` 方法通过菱形继承路径到达,但实际上是安全的。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrD3DTexture` | 提供纹理功能基类 |
| `GrD3DRenderTarget` | 提供渲染目标功能基类 |
| `GrD3DTextureResource` | 资源创建和初始化 |
| `GrD3DGpu` | GPU 设备访问和资源提供者 |
| `GrD3DResourceState` | D3D12 资源状态跟踪 |
| `GrD3DDescriptorHeap` | 描述符句柄管理 |
| `GrSurface` | 表面基类(虚拟继承) |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrD3DGpu` | 创建纹理渲染目标资源 |
| `GrD3DResourceProvider` | 通过工厂方法获取纹理渲染目标 |
| Surface 创建流程 | 需要同时具备纹理和渲染能力的表面 |

## 设计模式与设计决策

### 多重继承组合模式

通过多重继承实现功能组合而非委托:
- **优势**: 类型系统自然支持,可同时用作纹理和渲染目标
- **挑战**: 需要仔细管理菱形继承和调用顺序
- **权衡**: 增加了复杂度但提供了类型安全和零成本抽象

### 工厂方法模式

提供两个静态工厂方法而非公共构造函数:
- `MakeNewTextureRenderTarget`: 创建 Skia 管理的新资源
- `MakeWrappedTextureRenderTarget`: 封装外部资源

这种分离明确区分了资源所有权和生命周期管理策略。

### 构造函数重载策略

四个私有构造函数形成 2x2 矩阵:
- 维度 1: MSAA vs 非 MSAA
- 维度 2: 新建 vs 封装

这避免了在构造函数中使用条件分支,每个构造函数职责单一。

### 资源状态初始化

根据使用模式选择合适的初始状态:
- MSAA 资源设为 `RESOLVE_DEST` - 预期会进行解析操作
- 非 MSAA 资源设为 `RENDER_TARGET` - 直接渲染
- 这种预设减少了后续的资源屏障转换

### Clear Value 语义化

不同场景使用不同的默认清除颜色:
- 新建 MSAA: 透明黑色 - 假设用于蒙版渲染
- 封装 MSAA: 不透明白色 - 通用场景的安全默认值

这体现了对常见使用模式的优化。

## 性能考量

### 描述符视图创建

在对象构造时立即创建所有需要的描述符视图:
- 着色器资源视图(SRV) - 用于纹理采样
- 渲染目标视图(RTV) - 用于渲染输出
- 避免运行时创建的开销

### MSAA 内存权衡

MSAA 模式需要额外的 GPU 内存:
- MSAA 表面: `width * height * sampleCnt * bytesPerPixel`
- 解析目标: `width * height * bytesPerPixel`
- 总内存是非 MSAA 的 `(sampleCnt + 1)` 倍

### 缓存注册

通过 `registerWithCache` 或 `registerWithCacheWrapped` 将资源纳入 GPU 缓存:
- 允许资源重用
- 支持预算管理
- 响应内存压力时可释放资源

### 虚拟继承开销

虚拟继承引入轻微的性能成本:
- 额外的虚表指针
- 间接访问基类成员
- 在 Skia 的使用场景中,这个开销被正确性和设计清晰度的收益所抵消

### 资源转换优化

通过正确的初始状态设置减少资源屏障:
- 创建时就处于正确状态
- 减少首次使用时的状态转换
- 提高命令缓冲区记录效率

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DTexture.h` | 父类 | 纹理功能基类 |
| `src/gpu/ganesh/d3d/GrD3DRenderTarget.h` | 父类 | 渲染目标功能基类 |
| `src/gpu/ganesh/d3d/GrD3DTextureResource.h` | 间接父类 | 底层资源管理 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | 依赖 | GPU 设备接口 |
| `src/gpu/ganesh/d3d/GrD3DResourceState.h` | 依赖 | 资源状态跟踪 |
| `src/gpu/ganesh/d3d/GrD3DDescriptorHeap.h` | 依赖 | 描述符堆管理 |
| `src/gpu/ganesh/GrTexture.h` | 间接基类 | Ganesh 纹理抽象 |
| `src/gpu/ganesh/GrRenderTarget.h` | 间接基类 | Ganesh 渲染目标抽象 |
| `src/gpu/ganesh/GrSurface.h` | 共享基类 | GPU 表面抽象 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | D3D12 类型定义 |
