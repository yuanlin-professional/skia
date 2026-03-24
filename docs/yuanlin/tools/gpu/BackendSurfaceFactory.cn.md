# BackendSurfaceFactory

> 源文件
> - tools/gpu/BackendSurfaceFactory.h
> - tools/gpu/BackendSurfaceFactory.cpp

## 概述

`BackendSurfaceFactory` 是 Skia GPU 工具集中用于创建后端纹理和渲染目标 Surface 的工厂模块。Surface 是 Skia 中进行绘图操作的画布，而后端 Surface 是直接由 GPU 纹理或渲染目标支持的高性能绘图表面。该模块封装了复杂的 GPU 资源创建和生命周期管理逻辑，提供简洁的 API 供测试和工具代码使用。

核心功能包括：创建基于后端纹理的 Surface（可用作纹理采样和渲染目标）、创建纯渲染目标 Surface（不可采样）、支持多重采样（MSAA）和 mipmap、自动管理 GPU 资源生命周期、支持 Ganesh 和 Graphite 两种 GPU 后端。该模块与 `ManagedBackendTexture` 紧密协作，确保创建的后端资源在 Surface 销毁时正确释放。

## 架构位置

`BackendSurfaceFactory` 位于 `tools/gpu/` 目录下，属于 GPU 测试工具层。在 Skia 架构中的位置：

1. **测试基础设施层**：为单元测试、GM 测试和基准测试提供标准化的 GPU Surface 创建能力
2. **资源管理抽象层**：封装不同 GPU 后端的资源创建差异，提供统一接口
3. **Surface 工厂模式**：实现工厂设计模式，隔离复杂的创建逻辑

该模块的依赖关系：
- **上游依赖**：`SkSurface`（Skia 核心 Surface 抽象）、`ManagedBackendTexture`（后端纹理管理）
- **后端依赖**：Ganesh（`GrDirectContext`）或 Graphite（`skgpu::graphite::Recorder`）
- **下游使用**：测试框架、GM 测试、性能基准测试、示例代码

特殊支持：Dawn 后端的 `MakeBackendTextureViewSurface` 提供了 WebGPU 特有的 TextureView 封装。

## 主要类与结构体

### sk_gpu_test 命名空间

所有函数位于 `sk_gpu_test` 命名空间中，表明这是测试工具代码。

### Ganesh 后端函数

#### MakeBackendTextureSurface（纹理 Surface）

两个重载版本，支持从 `SkImageInfo` 或分离参数创建。

**完整版本：**
```cpp
sk_sp<SkSurface> MakeBackendTextureSurface(
    GrDirectContext* dContext,
    const SkImageInfo& ii,
    GrSurfaceOrigin origin,
    int sampleCnt,
    skgpu::Mipmapped mipmapped,
    GrProtected isProtected,
    const SkSurfaceProps* props);
```

创建一个由后端纹理支持的 Surface，该纹理既可以作为渲染目标，也可以作为纹理采样源。

#### MakeBackendRenderTargetSurface（纯渲染目标 Surface）

两个重载版本，创建不可采样的渲染目标。

**完整版本：**
```cpp
sk_sp<SkSurface> MakeBackendRenderTargetSurface(
    GrDirectContext* dContext,
    const SkImageInfo& ii,
    GrSurfaceOrigin origin,
    int sampleCnt,
    GrProtected isProtected,
    const SkSurfaceProps* props);
```

创建一个纯渲染目标 Surface，不支持作为纹理使用，但可能在某些硬件上更高效。

### Graphite 后端函数

#### MakeBackendTextureSurface（Graphite 版本）

```cpp
sk_sp<SkSurface> MakeBackendTextureSurface(
    skgpu::graphite::Recorder* recorder,
    const SkImageInfo& ii,
    skgpu::Mipmapped mipmapped,
    skgpu::Protected isProtected,
    const SkSurfaceProps* props);
```

Graphite 版本的纹理 Surface 创建函数，使用 Recorder 而非 Context。

#### MakeBackendTextureViewSurface（Dawn 专用）

```cpp
sk_sp<SkSurface> MakeBackendTextureViewSurface(
    skgpu::graphite::Recorder* recorder,
    const SkImageInfo& ii,
    skgpu::Mipmapped mipmapped,
    skgpu::Protected isProtected,
    const SkSurfaceProps* props);
```

仅在 Dawn（WebGPU）后端可用，封装 `WGPUTextureView` 而非直接使用纹理。

### 内部辅助结构（Ganesh）

#### ReleaseContext（匿名命名空间）

```cpp
struct ReleaseContext {
    sk_sp<GrDirectContext> fContext;
    GrBackendRenderTarget fRenderTarget;
};
```

用于渲染目标 Surface 的释放上下文，存储 Context 引用和渲染目标句柄，确保资源正确释放。

## 公共 API 函数

### MakeBackendTextureSurface（Ganesh，从 SkImageInfo）

```cpp
sk_sp<SkSurface> MakeBackendTextureSurface(
    GrDirectContext* dContext,
    const SkImageInfo& ii,
    GrSurfaceOrigin origin,
    int sampleCnt,
    skgpu::Mipmapped mipmapped = skgpu::Mipmapped::kNo,
    GrProtected isProtected = GrProtected::kNo,
    const SkSurfaceProps* props = nullptr);
```

**参数：**
- `dContext`：Direct GPU 上下文
- `ii`：图像信息（尺寸、色彩类型、alpha 类型、色彩空间）
- `origin`：Surface 原点（`kTopLeft` 或 `kBottomLeft`）
- `sampleCnt`：多重采样数（1 表示无 MSAA）
- `mipmapped`：是否创建 mipmap 链
- `isProtected`：是否为受保护内存（DRM 内容）
- `props`：Surface 属性（文本渲染设置等）

**返回值：** 创建的 Surface，失败返回 `nullptr`

**限制：** 不支持 `kUnpremul_SkAlphaType`（必须是预乘或不透明）

### MakeBackendTextureSurface（Ganesh，分离参数）

```cpp
sk_sp<SkSurface> MakeBackendTextureSurface(
    GrDirectContext* dContext,
    SkISize dimensions,
    GrSurfaceOrigin origin,
    int sampleCnt,
    SkColorType colorType,
    sk_sp<SkColorSpace> colorSpace = nullptr,
    skgpu::Mipmapped mipmapped = skgpu::Mipmapped::kNo,
    GrProtected isProtected = GrProtected::kNo,
    const SkSurfaceProps* props = nullptr);
```

便利重载，将尺寸、色彩类型和色彩空间作为单独参数，内部构造 `SkImageInfo` 后调用主版本。强制使用 `kPremul_SkAlphaType`。

### MakeBackendRenderTargetSurface（Ganesh，从 SkImageInfo）

```cpp
sk_sp<SkSurface> MakeBackendRenderTargetSurface(
    GrDirectContext* dContext,
    const SkImageInfo& ii,
    GrSurfaceOrigin origin,
    int sampleCnt,
    GrProtected isProtected = GrProtected::kNo,
    const SkSurfaceProps* props = nullptr);
```

创建纯渲染目标 Surface，不可作为纹理采样。

**参数：** 与纹理版本类似，但没有 `mipmapped` 参数（渲染目标不需要 mipmap）

**限制：** 不支持 `kUnpremul_SkAlphaType` 和 `kUnknown_SkAlphaType`

### MakeBackendRenderTargetSurface（Ganesh，分离参数）

便利重载，与纹理版本对应。

### MakeBackendTextureSurface（Graphite）

```cpp
sk_sp<SkSurface> MakeBackendTextureSurface(
    skgpu::graphite::Recorder* recorder,
    const SkImageInfo& ii,
    skgpu::Mipmapped mipmapped = skgpu::Mipmapped::kNo,
    skgpu::Protected isProtected = skgpu::Protected::kNo,
    const SkSurfaceProps* props = nullptr);
```

Graphite 版本，使用 `Recorder` 代替 `GrDirectContext`。注意：Graphite 不需要显式指定 origin 和 sampleCnt（由内部决定）。

### MakeBackendTextureViewSurface（Graphite + Dawn）

```cpp
sk_sp<SkSurface> MakeBackendTextureViewSurface(
    skgpu::graphite::Recorder* recorder,
    const SkImageInfo& ii,
    skgpu::Mipmapped mipmapped = skgpu::Mipmapped::kNo,
    skgpu::Protected isProtected = skgpu::Protected::kNo,
    const SkSurfaceProps* props = nullptr);
```

仅限 Dawn 后端，通过 `WGPUTextureView` 封装纹理。这对于与 WebGPU 渲染管线互操作很有用。

**限制：** 必须在 Dawn 后端上运行，否则返回 `nullptr`

## 内部实现细节

### Ganesh 纹理 Surface 创建流程

1. **验证 Alpha 类型**：拒绝 `kUnpremul_SkAlphaType`
2. **创建托管后端纹理**：使用 `ManagedBackendTexture::MakeWithoutData()` 创建空纹理
3. **封装为 Surface**：调用 `SkSurfaces::WrapBackendTexture()` 将纹理封装为 Surface
4. **注册释放回调**：设置 `ManagedBackendTexture::ReleaseProc` 作为释放回调，确保 Surface 销毁时纹理也被删除

关键代码：
```cpp
auto mbet = ManagedBackendTexture::MakeWithoutData(dContext, ...);
return SkSurfaces::WrapBackendTexture(dContext,
                                      mbet->texture(),
                                      origin, sampleCnt, colorType, colorSpace, props,
                                      ManagedBackendTexture::ReleaseProc,
                                      mbet->releaseContext());
```

### Ganesh 渲染目标 Surface 创建流程

1. **验证 Alpha 类型**：拒绝 `kUnpremul` 和 `kUnknown`
2. **转换色彩类型**：使用 `SkColorTypeToGrColorType()` 转换为 Ganesh 内部色彩类型
3. **创建测试渲染目标**：调用 `GrGpu::createTestingOnlyBackendRenderTarget()`，这是一个专门用于测试的 API
4. **构造释放上下文**：创建 `ReleaseContext` 存储上下文和渲染目标句柄
5. **封装为 Surface**：使用 `SkSurfaces::WrapBackendRenderTarget()`
6. **注册 Lambda 释放回调**：在回调中删除测试渲染目标

关键代码：
```cpp
auto bert = dContext->priv().getGpu()->createTestingOnlyBackendRenderTarget(...);
auto rc = new ReleaseContext{sk_ref_sp(dContext), bert};
auto proc = [](void* c) {
    const auto* rc = static_cast<ReleaseContext*>(c);
    if (auto gpu = rc->fContext->priv().getGpu(); gpu && rc->fRenderTarget.isValid()) {
        gpu->deleteTestingOnlyBackendRenderTarget(rc->fRenderTarget);
    }
    delete rc;
};
return SkSurfaces::WrapBackendRenderTarget(dContext, bert, origin, colorType, colorSpace, props, proc, rc);
```

### Graphite 纹理 Surface 创建流程

1. **创建托管纹理**：使用 `ManagedGraphiteTexture::MakeUnInit()` 创建未初始化的纹理
2. **封装为 Surface**：调用 `SkSurfaces::WrapBackendTexture()`
3. **注册释放回调**：设置 `ManagedGraphiteTexture::ReleaseProc`

Graphite 的实现更简洁，因为：
- 不需要显式指定 origin（Graphite 统一使用 top-left）
- 不需要显式 sampleCnt（由 Recorder 的能力决定）
- 使用 Recorder 而非 Context，符合 Graphite 的命令记录模型

### Dawn TextureView 创建流程（Graphite）

1. **验证后端类型**：确保运行在 Dawn 后端
2. **创建托管纹理**：与普通 Graphite 相同
3. **提取 Dawn 纹理**：使用 `BackendTextures::GetDawnTexturePtr()` 获取底层 `wgpu::Texture`
4. **创建 TextureView**：调用 `texture.CreateView()` 创建 WebGPU TextureView
5. **构造 TextureInfo**：从原始纹理提取格式、用途等信息
6. **从 TextureView 创建 BackendTexture**：使用 `BackendTextures::MakeDawn()` 封装 TextureView
7. **封装为 Surface**：传递新的 BackendTexture 到 `SkSurfaces::WrapBackendTexture()`

这个流程的特殊之处在于使用了 TextureView 而非直接使用 Texture，这在 WebGPU 中很常见，因为 View 提供了额外的配置灵活性（如特定 mip 层级、数组切片等）。

### 资源生命周期管理

所有创建的 Surface 都通过释放回调管理底层 GPU 资源：

- **纹理 Surface**：`ManagedBackendTexture` 的引用计数在释放回调中递减，当计数归零时自动删除纹理
- **渲染目标 Surface**：Lambda 捕获的 `ReleaseContext` 在回调中被删除，同时调用 `deleteTestingOnlyBackendRenderTarget()`

这确保即使 Surface 的生命周期由外部控制，底层 GPU 资源也会在适当时机释放。

### 条件编译策略

使用 `#if defined(SK_GANESH)` 和 `#ifdef SK_GRAPHITE` 将不同后端的代码隔离：
- 允许选择性编译后端
- 避免链接未使用后端的库
- 保持 API 一致性（函数名相同，参数适配后端特性）

Dawn 特有功能额外使用 `#if defined(SK_DAWN)` 保护。

## 依赖关系

### 核心依赖

- **SkSurface**：Skia 的 Surface 抽象
- **SkImageInfo**：图像元数据（尺寸、格式、色彩空间）
- **SkColorSpace**：色彩空间管理
- **ManagedBackendTexture / ManagedGraphiteTexture**：自动管理后端纹理生命周期

### Ganesh 依赖

- **GrDirectContext**：Ganesh GPU 上下文
- **GrBackendSurface**：后端 Surface 封装（纹理和渲染目标）
- **GrGpu**：底层 GPU 接口（用于创建测试渲染目标）
- **SkSurfaceGanesh**：Ganesh 特定的 Surface 工厂函数

### Graphite 依赖

- **skgpu::graphite::Recorder**：Graphite 命令记录器
- **skgpu::graphite::BackendTexture**：Graphite 后端纹理
- **skgpu::graphite::Surface**：Graphite Surface 工厂函数

### Dawn 特定依赖

- **webgpu_cpp.h**：WebGPU C++ 绑定
- **DawnGraphiteTypes.h / DawnGraphiteUtils.h**：Dawn 和 Graphite 的互操作工具

### 被依赖

- 测试框架（DM、GM）
- 性能基准测试
- 示例代码和教程
- GPU 功能验证测试

## 设计模式与设计决策

### 工厂模式

所有函数都是工厂方法，封装复杂的创建逻辑：
- 隐藏后端特定的创建细节
- 提供统一的参数接口
- 失败时返回 `nullptr`，简化错误处理

### RAII 和智能指针

使用 `sk_sp<SkSurface>` 返回 Surface：
- 自动管理引用计数
- 配合释放回调，确保 GPU 资源也被正确释放
- 避免手动内存管理的错误

### 释放回调模式

通过回调函数（而非析构函数）管理 GPU 资源：
- Surface 的生命周期由用户控制，释放时机不确定
- 回调在 Surface 销毁时由 Skia 内部调用
- 支持传递上下文数据（如 `ManagedBackendTexture` 指针或 `ReleaseContext`）

### 函数重载

为便利性提供多个重载版本：
- 接受 `SkImageInfo` 的版本：适合已有完整元数据的场景
- 接受分离参数的版本：适合逐个指定属性的场景
- 内部统一转换为主版本，避免代码重复

### 托管资源（Managed Resources）

使用 `ManagedBackendTexture` 而非直接创建 `GrBackendTexture`：
- 简化生命周期管理
- 确保资源不会泄漏
- 支持复杂的释放场景（如 YUVA 多平面纹理）

### 特殊化 vs 通用化权衡

- **通用功能**：纹理 Surface 创建在两个后端都支持
- **特殊化功能**：Dawn 的 TextureView Surface 只在特定后端提供
- **条件编译**：使用宏隔离后端特定代码，保持代码整洁

### 测试优先的设计

- `createTestingOnlyBackendRenderTarget` 的命名明确表明这是测试专用 API
- 不鼓励在生产代码中使用，但对测试非常有用
- 允许创建不受常规 Surface 限制的特殊配置

## 性能考量

### 资源创建开销

创建后端 Surface 涉及 GPU 资源分配：
- **纹理**：分配 GPU 内存、可能初始化为零
- **渲染目标**：可能需要额外的深度/模板缓冲区
- **MSAA**：多重采样需要更多内存

建议：在性能关键代码中复用 Surface，避免频繁创建和销毁。

### Mipmap 生成

启用 `Mipmapped::kYes` 会增加内存占用（约 1/3 额外内存）并可能触发初始 mipmap 生成。建议只在需要纹理过滤的场景使用。

### 多重采样（MSAA）

`sampleCnt > 1` 会显著增加内存和填充率开销：
- 典型值：4x 或 8x MSAA
- 内存开销：渲染目标内存乘以采样数
- 性能开销：每个片段需要多次着色

### 受保护内存

`Protected::kYes` 用于 DRM 内容，可能有性能影响：
- 限制 CPU 访问
- 可能限制某些优化
- 仅在需要时使用

### 后端差异

- **Ganesh**：成熟稳定，但创建流程较复杂
- **Graphite**：新架构，资源管理更现代化，但仍在开发中
- **Dawn/WebGPU**：跨平台，但可能有额外的抽象开销

### 测试渲染目标 vs 正式渲染目标

`createTestingOnlyBackendRenderTarget` 创建的渲染目标可能：
- 绕过某些验证检查
- 使用不同的内存分配策略
- 不适合长期使用或生产环境

## 相关文件

### 核心依赖

- `include/core/SkSurface.h` - Surface 抽象接口
- `include/core/SkImageInfo.h` - 图像元数据
- `tools/gpu/ManagedBackendTexture.h` - 托管后端纹理

### Ganesh 相关

- `include/gpu/ganesh/GrDirectContext.h` - Ganesh 上下文
- `include/gpu/ganesh/SkSurfaceGanesh.h` - Ganesh Surface 工厂
- `include/gpu/ganesh/GrBackendSurface.h` - 后端 Surface 封装
- `src/gpu/ganesh/GrGpu.h` - 底层 GPU 接口

### Graphite 相关

- `include/gpu/graphite/Recorder.h` - Graphite 记录器
- `include/gpu/graphite/Surface.h` - Graphite Surface 工厂
- `include/gpu/graphite/BackendTexture.h` - Graphite 后端纹理

### Dawn 相关

- `include/gpu/graphite/dawn/DawnGraphiteTypes.h` - Dawn 类型定义
- `src/gpu/graphite/dawn/DawnGraphiteUtils.h` - Dawn 工具函数

### 使用场景

- `tests/` - GPU 单元测试
- `gm/` - GM 测试（Golden Master）
- `bench/` - 性能基准测试
- `tools/viewer/` - 示例查看器

### 相关工具类

- `tools/gpu/GrContextFactory.h` - GPU 上下文工厂
- `tools/gpu/ProxyUtils.h` - GPU 代理工具
