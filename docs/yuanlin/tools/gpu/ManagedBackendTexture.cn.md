# ManagedBackendTexture

> 源文件
> - tools/gpu/ManagedBackendTexture.h
> - tools/gpu/ManagedBackendTexture.cpp

## 概述

`ManagedBackendTexture` 是 Skia GPU 工具集中用于自动管理后端纹理生命周期的 RAII 封装类。在 GPU 编程中，纹理资源的手动管理容易导致内存泄漏或过早释放。该模块提供了智能引用计数的纹理封装，确保纹理在不再被使用时自动释放，同时支持与 Skia 的 Surface 和 Image 系统集成。

核心功能包括：自动管理 GPU 纹理生命周期、支持带数据和不带数据的纹理创建、提供释放回调机制与 Skia Image/Surface 集成、支持 YUVA 多平面纹理的统一释放、同时支持 Ganesh 和 Graphite 两种 GPU 后端。该模块通过引用计数和回调函数实现资源的自动释放，显著简化了测试和工具代码中的 GPU 资源管理。

## 架构位置

`ManagedBackendTexture` 位于 `tools/gpu/` 目录下，是 GPU 测试工具层的核心组件之一。在 Skia 架构中：

1. **资源管理层**：封装底层的 `GrBackendTexture` 或 `skgpu::graphite::BackendTexture`，提供自动生命周期管理
2. **回调桥接层**：实现 Skia 释放回调接口，连接用户代码和 GPU 资源释放逻辑
3. **测试基础设施**：被 `BackendSurfaceFactory`、`YUVUtils` 等工具类广泛使用

依赖关系：
- **上游依赖**：`SkRefCnt`（引用计数基类）、`SkPixmap`、`SkBitmap`（像素数据源）
- **后端依赖**：Ganesh 的 `GrDirectContext` 或 Graphite 的 `Recorder`/`Context`
- **下游使用**：Surface 和 Image 工厂函数、测试用例、工具代码

## 主要类与结构体

### ManagedBackendTexture（Ganesh 版本）

继承自 `SkNVRefCnt<ManagedBackendTexture>`，使用非虚引用计数管理生命周期。

**关键成员变量：**
- `sk_sp<GrDirectContext> fDContext`：持有 GPU 上下文的强引用，确保上下文在纹理释放前有效
- `GrBackendTexture fTexture`：封装的后端纹理对象

**关键特性：**
- 禁用拷贝和移动构造/赋值（确保唯一所有权）
- 私有构造函数（只能通过工厂方法创建）
- 析构函数中自动删除后端纹理

### ManagedGraphiteTexture（Graphite 版本）

Graphite 后端的对应实现，API 设计与 Ganesh 版本平行。

**关键成员变量：**
- `skgpu::graphite::Context* fContext`：Graphite 上下文原始指针（生命周期由外部保证）
- `skgpu::graphite::BackendTexture fTexture`：Graphite 后端纹理对象

**关键差异：**
- 使用 `Recorder` 创建纹理，但存储 `Context` 用于删除
- 提供 `FinishedProc` 支持 Graphite 的异步完成回调
- 支持从压缩数据创建纹理

### Context 结构体（Ganesh，匿名命名空间）

```cpp
struct Context {
    GrGpuFinishedProc fWrappedProc;
    GrGpuFinishedContext fWrappedContext;
    sk_sp<ManagedBackendTexture> fMBETs[SkYUVAInfo::kMaxPlanes];
};
```

释放上下文结构，支持：
- 嵌套回调（`fWrappedProc/fWrappedContext`）
- 单个或多个（YUVA）纹理的引用

### MBETContext 结构体（Graphite，匿名命名空间）

```cpp
struct MBETContext {
    sk_sp<ManagedGraphiteTexture> fMBETs[SkYUVAInfo::kMaxPlanes];
};
```

Graphite 的释放上下文，更简单（不需要嵌套回调支持）。

## 公共 API 函数

### Ganesh API

#### MakeWithData（模板工厂方法）

```cpp
template <typename... Args>
static sk_sp<ManagedBackendTexture> MakeWithData(GrDirectContext* dContext, Args&&... args);
```

创建带初始数据的托管纹理。参数可以是任何 `GrDirectContext::createBackendTexture` 接受的参数（除了释放回调，由该类自动提供）。

**使用示例：**
```cpp
auto mbet = ManagedBackendTexture::MakeWithData(dContext, pixmap, mipmapped, renderable, protected);
```

**特点：**
- 完美转发参数到 `createBackendTexture`
- 自动注册释放回调
- 数据上传在创建时完成

#### MakeWithoutData（模板工厂方法）

```cpp
template <typename... Args>
static sk_sp<ManagedBackendTexture> MakeWithoutData(GrDirectContext* dContext, Args&&... args);
```

创建不带初始数据的托管纹理（纹理内容未定义或已初始化为零）。

**警告：** 如果使用带数据的 `createBackendTexture` 重载但通过此方法调用，无法保证数据上传完成后才删除纹理。应使用 `MakeWithData` 避免此问题。

#### MakeFromInfo

```cpp
static sk_sp<ManagedBackendTexture> MakeFromInfo(
    GrDirectContext* dContext,
    const SkImageInfo& ii,
    skgpu::Mipmapped mipmapped,
    skgpu::Renderable renderable,
    skgpu::Protected isProtected);
```

从 `SkImageInfo` 创建空纹理（便利方法，内部调用 `MakeWithoutData`）。

#### MakeFromBitmap

```cpp
static sk_sp<ManagedBackendTexture> MakeFromBitmap(
    GrDirectContext* dContext,
    const SkBitmap& bitmap,
    skgpu::Mipmapped mipmapped,
    skgpu::Renderable renderable,
    skgpu::Protected isProtected);
```

从 `SkBitmap` 创建并上传纹理数据。如果需要 mipmap，自动生成所有层级。

#### MakeFromPixmap

```cpp
static sk_sp<ManagedBackendTexture> MakeFromPixmap(
    GrDirectContext* dContext,
    const SkPixmap& pixmap,
    skgpu::Mipmapped mipmapped,
    skgpu::Renderable renderable,
    skgpu::Protected isProtected);
```

从 `SkPixmap` 创建并上传纹理数据。支持 mipmap 自动生成。

#### ReleaseProc

```cpp
static void ReleaseProc(void* context);
```

静态释放回调函数，传递给 Skia 的 Image/Surface 创建函数。从 `void*` 上下文恢复 `Context` 结构体，调用嵌套回调（如果有），然后释放纹理引用。

#### releaseContext

```cpp
void* releaseContext(GrGpuFinishedProc wrappedProc = nullptr,
                     GrGpuFinishedContext wrappedContext = nullptr) const;
```

创建释放上下文（`Context*`），增加引用计数。必须配合 `ReleaseProc` 使用以平衡引用。

**参数：**
- `wrappedProc`：可选的嵌套回调函数
- `wrappedContext`：嵌套回调的上下文

**返回值：** `Context*` 指针，强制转换为 `void*`

#### refCountedCallback

```cpp
sk_sp<skgpu::RefCntedCallback> refCountedCallback() const;
```

创建引用计数的回调对象，用于需要 `RefCntedCallback` 接口的场景。

#### wasAdopted

```cpp
void wasAdopted();
```

标记纹理已被 GrContext 采纳（ownership 转移），清空内部纹理句柄，避免重复释放。

#### MakeYUVAReleaseContext

```cpp
static void* MakeYUVAReleaseContext(
    const sk_sp<ManagedBackendTexture> mbets[SkYUVAInfo::kMaxPlanes]);
```

为 YUVA 多平面纹理创建统一的释放上下文。`SkImages::TextureFromYUVATextures` 接受单个释放回调管理所有平面，此方法创建持有所有平面引用的 `Context`。

### Graphite API

#### MakeUnInit

```cpp
static sk_sp<ManagedGraphiteTexture> MakeUnInit(
    Recorder* recorder,
    const SkImageInfo& ii,
    skgpu::Mipmapped mipmapped,
    skgpu::Renderable renderable,
    skgpu::Protected isProtected);
```

创建未初始化的 Graphite 纹理。内容未定义，需要后续调用 `updateBackendTexture` 上传数据。

#### MakeFromPixmap

```cpp
static sk_sp<ManagedGraphiteTexture> MakeFromPixmap(
    Recorder* recorder,
    const SkPixmap& pixmap,
    skgpu::Mipmapped mipmapped,
    skgpu::Renderable renderable,
    skgpu::Protected isProtected);
```

从 `SkPixmap` 创建并上传纹理数据。支持 mipmap 自动生成。

#### MakeMipmappedFromPixmaps

```cpp
static sk_sp<ManagedGraphiteTexture> MakeMipmappedFromPixmaps(
    Recorder* recorder,
    SkSpan<const SkPixmap> levels,
    skgpu::Renderable renderable,
    skgpu::Protected isProtected);
```

从预先生成的 mipmap 层级数组创建纹理。允许用户完全控制每个 mip 层级的内容。

#### MakeFromCompressedData

```cpp
static sk_sp<ManagedGraphiteTexture> MakeFromCompressedData(
    Recorder* recorder,
    SkISize dimensions,
    SkTextureCompressionType compressionType,
    sk_sp<SkData> data,
    skgpu::Mipmapped mipmapped,
    skgpu::Protected isProtected);
```

从压缩数据（如 BC1、ETC2）创建纹理。这是 Graphite 特有的功能（Ganesh 版本未实现）。

#### FinishedProc / ReleaseProc / ImageReleaseProc

```cpp
static void FinishedProc(void* context, skgpu::CallbackResult);
static void ReleaseProc(void* context);
static void ImageReleaseProc(void* context);
```

三种释放回调函数：
- `FinishedProc`：用于 `Recorder::addFinishInfo` 的完成回调
- `ReleaseProc`：通用释放回调
- `ImageReleaseProc`：用于 Image 的释放回调

实现相同：销毁 `MBETContext` 并释放纹理引用。

#### releaseContext

```cpp
void* releaseContext() const;
```

创建 Graphite 释放上下文，增加引用计数。

#### refCountedCallback

```cpp
sk_sp<skgpu::RefCntedCallback> refCountedCallback() const;
```

创建引用计数的回调对象（与 Ganesh 版本类似）。

#### MakeYUVAReleaseContext

```cpp
static void* MakeYUVAReleaseContext(
    const sk_sp<ManagedGraphiteTexture> mbets[SkYUVAInfo::kMaxPlanes]);
```

Graphite 版本的 YUVA 释放上下文创建。

## 内部实现细节

### 引用计数生命周期

典型的生命周期流程：

1. **创建**：工厂方法（如 `MakeFromPixmap`）创建 MBET 对象，引用计数为 1
2. **使用**：用户代码持有 `sk_sp<ManagedBackendTexture>`
3. **传递给 Skia**：调用 `releaseContext()` 增加引用（现在为 2），将上下文指针传给 Image/Surface
4. **用户释放**：`sk_sp` 离开作用域，引用计数减至 1
5. **Skia 释放**：Image/Surface 销毁时调用 `ReleaseProc`，引用计数减至 0
6. **自动清理**：引用计数归零触发析构函数，删除后端纹理

### Ganesh 纹理创建流程（带数据）

```cpp
sk_sp<ManagedBackendTexture> mbet(new ManagedBackendTexture);
mbet->fDContext = sk_ref_sp(dContext);
mbet->fTexture = dContext->createBackendTexture(
    std::forward<Args>(args)...,
    ReleaseProc,
    mbet->releaseContext()
);
```

关键点：
- 使用完美转发传递用户参数
- 自动附加 `ReleaseProc` 和释放上下文
- 纹理创建失败时返回 `nullptr`（通过 `fTexture.isValid()` 检查）

### Graphite 纹理创建流程（从 Pixmap）

```cpp
sk_sp<ManagedGraphiteTexture> mbet = MakeUnInit(recorder, info, mipmapped, renderable, protected);
// 生成 mipmap 层级
std::vector<SkPixmap> levels = {basePixmap, mip1, mip2, ...};
recorder->updateBackendTexture(mbet->fTexture, levels.data(), levels.size());
```

Graphite 的两阶段创建：
1. 分配纹理内存（`createBackendTexture`）
2. 上传数据（`updateBackendTexture`）

优点：
- 允许异步上传
- 支持分批上传 mipmap 层级
- 更灵活的错误处理

### Mipmap 自动生成

`MakeFromPixmap` 中的 mipmap 生成逻辑：

```cpp
if (mipmapped == Mipmapped::kYes) {
    mm.reset(SkMipmap::Build(src, nullptr));  // 使用 SkMipmap 生成金字塔
    for (int i = 0; i < mm->countLevels(); ++i) {
        SkMipmap::Level level;
        mm->getLevel(i, &level);
        levels.push_back(level.fPixmap);  // 收集所有层级
    }
}
```

生成的 mipmap 使用盒式滤波器（box filter），适合一般用途。

### YUVA 多平面释放机制

YUVA 图像使用多个纹理（Y、U、V、A 平面），但 Skia 的 YUVA API 只接受单个释放回调。`MakeYUVAReleaseContext` 解决此问题：

```cpp
auto context = new Context;
for (int i = 0; i < SkYUVAInfo::kMaxPlanes; ++i) {
    context->fMBETs[i] = mbets[i];  // 持有所有平面的引用
}
return context;
```

当 Image 销毁时，`ReleaseProc` 释放 `Context`，其析构函数自动释放所有平面的引用。

### 嵌套回调支持（Ganesh）

`releaseContext` 支持嵌套回调：

```cpp
void* releaseContext(GrGpuFinishedProc wrappedProc, GrGpuFinishedContext wrappedCtx) const {
    return new Context{wrappedProc, wrappedCtx, {sk_ref_sp(this)}};
}
```

`ReleaseProc` 中先调用嵌套回调：

```cpp
if (context->fWrappedProc) {
    context->fWrappedProc(context->fWrappedContext);
}
```

这允许用户在纹理释放前执行自定义逻辑。

### Graphite 的异步完成机制

Graphite 使用 `addFinishInfo` 注册完成回调：

```cpp
recorder->addFinishInfo({mbet->releaseContext(), FinishedProc});
```

当 GPU 完成纹理上传后，调用 `FinishedProc` 释放上传缓冲区。这与纹理本身的释放分离，允许更细粒度的资源管理。

### wasAdopted 的用途

某些场景下，纹理的所有权转移给 GrContext（如通过 `adoptBackendTexture`）。此时需要调用 `wasAdopted()` 清空 MBET 的纹理句柄：

```cpp
void wasAdopted() { fTexture = {}; }
```

否则析构函数会尝试删除已被 Context 管理的纹理，导致双重释放。

## 依赖关系

### 核心依赖

- **SkRefCnt / SkNVRefCnt**：引用计数基类
- **SkBitmap / SkPixmap**：像素数据容器
- **SkImageInfo**：图像元数据
- **SkMipmap**：Mipmap 生成工具
- **SkYUVAInfo**：YUV 平面配置信息
- **skgpu::RefCntedCallback**：引用计数的回调封装

### Ganesh 依赖

- **GrDirectContext**：GPU 上下文，提供纹理创建和删除接口
- **GrBackendSurface**：后端纹理封装
- **GrTypesPriv**：Ganesh 内部类型定义

### Graphite 依赖

- **skgpu::graphite::Recorder**：命令记录器，用于创建和更新纹理
- **skgpu::graphite::Context**：GPU 上下文，用于删除纹理
- **skgpu::graphite::BackendTexture**：Graphite 后端纹理
- **skgpu::graphite::Caps**：能力查询接口

### 被依赖

- **BackendSurfaceFactory**：使用 MBET 创建 Surface
- **YUVUtils**：LazyYUVImage 使用 MBET 管理 YUVA 平面
- 测试代码（tests/、gm/）
- 工具代码（tools/viewer/、tools/skiaserve/）

## 设计模式与设计决策

### RAII（Resource Acquisition Is Initialization）

核心设计原则：
- 资源获取（纹理创建）即初始化
- 资源释放（纹理删除）在析构函数中自动进行
- 通过智能指针管理生命周期

### 工厂方法模式

所有构造函数私有，只能通过工厂方法创建：
- 控制对象创建流程
- 失败时返回 `nullptr`，而非抛出异常或返回无效对象
- 允许不同创建方式（有/无数据、从 Pixmap/Bitmap/Info）

### 回调模式

使用函数指针作为释放回调：
- 符合 C 风格 API 要求（Skia 的 Image/Surface API）
- 通过 `void*` 上下文传递状态
- 支持嵌套回调（Ganesh）和多种回调类型（Graphite）

### 智能指针 + 引用计数

使用 `sk_sp` 和 `SkNVRefCnt`：
- 自动管理引用计数
- 线程安全的引用操作（原子操作）
- 避免循环引用（使用非虚引用计数）

### 模板元编程（完美转发）

`MakeWithData` 和 `MakeWithoutData` 使用可变参数模板：
- 接受任意参数组合
- 零开销转发到底层 API
- 类型安全（编译时检查）

### 两阶段创建（Graphite）

Graphite 的 `MakeUnInit` + `updateBackendTexture` 分离纹理分配和数据上传：
- **优点**：支持异步上传、分批上传、更灵活的错误处理
- **代价**：需要显式调用两个步骤

### 平台特定优化

- **Ganesh**：使用 `createBackendTexture` 的 upload 回调确保上传完成
- **Graphite**：使用 `addFinishInfo` 管理上传缓冲区生命周期
- **压缩纹理**：仅 Graphite 支持（通过 `MakeFromCompressedData`）

### 禁用拷贝和移动

```cpp
ManagedBackendTexture(const ManagedBackendTexture&) = delete;
ManagedBackendTexture(ManagedBackendTexture&&) = delete;
```

确保唯一所有权：
- 避免意外的纹理句柄复制
- 明确生命周期管理责任
- 强制使用智能指针传递

## 性能考量

### 引用计数开销

每次 `sk_sp` 复制或赋值都需要原子操作：
- 现代 CPU 上开销很小（通常几个时钟周期）
- 多线程场景下可能有缓存一致性开销
- 相对于 GPU 操作，可以忽略不计

### Mipmap 生成开销

自动生成 mipmap（`SkMipmap::Build`）的成本：
- CPU 端图像下采样，O(pixels) 时间复杂度
- 需要额外内存存储所有层级（约 1/3 额外内存）
- 对于大型纹理（如 4K 图像）可能需要数十毫秒

建议：对于频繁创建的小纹理，考虑预先生成 mipmap 或使用 `kNo` 禁用。

### GPU 内存分配

每次创建 MBET 都会分配 GPU 内存：
- 可能触发 GPU 内存管理（如碎片整理）
- 大型纹理或频繁创建可能导致性能问题

建议：在热循环中复用纹理，或使用纹理池。

### 上传带宽

从 CPU 到 GPU 的数据传输受 PCIe 带宽限制：
- 典型速度：数 GB/s（取决于 PCIe 版本）
- 大型纹理上传可能阻塞渲染管线

优化：
- 使用压缩纹理格式减少传输量
- 异步上传（Graphite 的 `updateBackendTexture`）
- 分帧上传大型纹理

### Graphite 的优势

Graphite 的两阶段创建允许更好的性能控制：
- 纹理分配和上传解耦
- 支持批量上传多个纹理
- 更细粒度的同步控制（通过 `addFinishInfo`）

### 测试场景的权衡

MBET 设计优先考虑便利性而非极致性能：
- 适合单次或少量纹理创建
- 引用计数和回调的开销在测试中可接受
- 生产代码可能需要更优化的资源管理策略

## 相关文件

### 核心依赖

- `include/core/SkRefCnt.h` - 引用计数基类
- `include/core/SkBitmap.h` - 位图容器
- `include/core/SkPixmap.h` - 像素映射
- `include/core/SkYUVAInfo.h` - YUVA 配置
- `src/core/SkMipmap.h` - Mipmap 生成
- `src/gpu/RefCntedCallback.h` - 引用计数回调

### Ganesh 相关

- `include/gpu/ganesh/GrDirectContext.h` - Ganesh 上下文
- `include/gpu/ganesh/GrBackendSurface.h` - 后端 Surface
- `include/private/gpu/ganesh/GrTypesPriv.h` - Ganesh 内部类型

### Graphite 相关

- `include/gpu/graphite/Recorder.h` - Graphite 记录器
- `include/gpu/graphite/Context.h` - Graphite 上下文
- `include/gpu/graphite/BackendTexture.h` - Graphite 后端纹理
- `src/gpu/graphite/Caps.h` - Graphite 能力查询
- `src/gpu/graphite/RecorderPriv.h` - Recorder 私有接口

### 使用场景

- `tools/gpu/BackendSurfaceFactory.h` - Surface 工厂（主要使用者）
- `tools/gpu/YUVUtils.h` - YUV 工具（YUVA 多平面场景）
- `tests/` - GPU 单元测试
- `gm/` - GM 测试

### 相关工具类

- `tools/gpu/FlushFinishTracker.h` - GPU 完成跟踪
- `tools/gpu/ProxyUtils.h` - GPU 代理工具
