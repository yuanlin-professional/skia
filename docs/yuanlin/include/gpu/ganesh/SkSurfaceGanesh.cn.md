# SkSurfaceGanesh

> 源文件: `include/gpu/ganesh/SkSurfaceGanesh.h`

## 概述
SkSurfaceGanesh 提供了基于 Ganesh GPU 后端创建和管理 SkSurface 的工厂函数集合。该模块是 Skia 渲染表面系统与 Ganesh GPU 渲染管线之间的桥梁,支持创建 GPU 渲染目标、包装后端纹理/渲染目标、获取底层 GPU 资源等操作。

## 架构位置
该文件位于 `include/gpu/ganesh` 公共 API 层,属于 Ganesh GPU 后端的表面管理子系统。它依赖核心的 SkSurface 抽象,并与 GrRecordingContext/GrDirectContext 紧密集成,为上层应用提供 GPU 加速的渲染目标创建能力。

## 命名空间结构

### SkSurfaces 命名空间
主要工厂函数封装在 `SkSurfaces` 命名空间中,遵循 Skia 现代 API 设计模式。

### skgpu::ganesh 命名空间
包含 Ganesh 特定的辅助函数,如 Flush 和 FlushAndSubmit。

## 核心类型定义

### 回调函数类型

#### ReleaseContext
```cpp
using ReleaseContext = void*;
```
- **用途**: 传递给释放回调的用户上下文指针

#### RenderTargetReleaseProc
```cpp
using RenderTargetReleaseProc = void (*)(ReleaseContext);
```
- **用途**: 当包装的渲染目标可以安全释放时调用

#### TextureReleaseProc
```cpp
using TextureReleaseProc = void (*)(ReleaseContext);
```
- **用途**: 当包装的纹理可以安全释放时调用

## 公共 API 函数 (SkSurfaces 命名空间)

### 创建渲染目标

#### `RenderTarget` (主版本)
```cpp
SK_API sk_sp<SkSurface> RenderTarget(
    GrRecordingContext* context,
    skgpu::Budgeted budgeted,
    const SkImageInfo& imageInfo,
    int sampleCount,
    GrSurfaceOrigin surfaceOrigin,
    const SkSurfaceProps* surfaceProps,
    bool shouldCreateWithMips = false,
    bool isProtected = false);
```

**功能**: 在 GPU 上创建渲染目标表面

**参数详解**:
| 参数 | 类型 | 说明 |
|------|------|------|
| context | GrRecordingContext* | GPU 上下文 |
| budgeted | skgpu::Budgeted | 是否计入 GPU 资源预算 |
| imageInfo | const SkImageInfo& | 图像信息(尺寸、颜色类型、Alpha 类型、色彩空间) |
| sampleCount | int | MSAA 采样数,0 表示禁用抗锯齿 |
| surfaceOrigin | GrSurfaceOrigin | 表面原点(kTopLeft 或 kBottomLeft) |
| surfaceProps | const SkSurfaceProps* | LCD 条纹方向和字体设置,可为 nullptr |
| shouldCreateWithMips | bool | 提示是否需要 mipmap 支持 |
| isProtected | bool | 是否使用受保护内存(DRM) |

**返回值**: 成功返回 SkSurface,失败返回 nullptr

**采样数处理**:
- 请求的采样数会向上舍入到下一个支持的值
- 如果超过最大支持值,向下舍入
- 传入 0 禁用 MSAA

**Mipmap 提示**:
- shouldCreateWithMips 暗示通过 makeImageSnapshot 创建的图像需要 mipmap
- 仅为提示,不保证一定创建

#### `RenderTarget` (简化版本)
```cpp
inline sk_sp<SkSurface> RenderTarget(
    GrRecordingContext* context,
    skgpu::Budgeted budgeted,
    const SkImageInfo& imageInfo,
    int sampleCount,
    const SkSurfaceProps* surfaceProps);
```
- **默认**: surfaceOrigin = kBottomLeft_GrSurfaceOrigin
- **应用**: 简化调用,使用默认方向

```cpp
inline sk_sp<SkSurface> RenderTarget(
    GrRecordingContext* context,
    skgpu::Budgeted budgeted,
    const SkImageInfo& imageInfo);
```
- **默认**: sampleCount = 0, surfaceOrigin = kBottomLeft
- **验证**: 宽度或高度为 0 时返回 nullptr

#### `RenderTarget` (从 Characterization)
```cpp
SK_API sk_sp<SkSurface> RenderTarget(
    GrRecordingContext* context,
    const GrSurfaceCharacterization& characterization,
    skgpu::Budgeted budgeted);
```

**功能**: 根据表面特征描述创建兼容的渲染目标

**参数**:
- `characterization`: 描述期望 SkSurface 的特征(DDL 录制场景)
- `budgeted`: 资源预算控制

**应用场景**: 延迟显示列表(DDL)录制

### 包装后端纹理

#### `WrapBackendTexture`
```cpp
SK_API sk_sp<SkSurface> WrapBackendTexture(
    GrRecordingContext* context,
    const GrBackendTexture& backendTexture,
    GrSurfaceOrigin origin,
    int sampleCnt,
    SkColorType colorType,
    sk_sp<SkColorSpace> colorSpace,
    const SkSurfaceProps* surfaceProps,
    TextureReleaseProc textureReleaseProc = nullptr,
    ReleaseContext releaseContext = nullptr);
```

**功能**: 将 GPU 后端纹理包装为 SkSurface

**前提条件**:
- 调用者确保纹理在 SkSurface 生命周期内有效
- backendTexture 的像素配置必须与 colorSpace 和 context 兼容

**MSAA 支持**:
- sampleCnt > 0 时创建中间 MSAA 表面用于绘制
- 绘制结果 resolve 到 backendTexture

**释放回调**:
- textureReleaseProc 在安全删除纹理时调用
- 失败时回调在函数返回前调用

**色彩空间匹配**:
- sRGB 纹理要求 context 支持 sRGB 且提供 colorSpace
- 纹理尺寸不能超过 context 能力限制

### 包装后端渲染目标

#### `WrapBackendRenderTarget`
```cpp
SK_API sk_sp<SkSurface> WrapBackendRenderTarget(
    GrRecordingContext* context,
    const GrBackendRenderTarget& backendRenderTarget,
    GrSurfaceOrigin origin,
    SkColorType colorType,
    sk_sp<SkColorSpace> colorSpace,
    const SkSurfaceProps* surfaceProps,
    RenderTargetReleaseProc releaseProc = nullptr,
    ReleaseContext releaseContext = nullptr);
```

**功能**: 将 GPU 后端渲染目标包装为 SkSurface

**参数**:
- `backendRenderTarget`: GPU 中间内存缓冲区
- 其他参数含义与 WrapBackendTexture 类似

**验证**:
- backendRenderTarget 必须与 colorSpace 和 context 兼容
- 尺寸不能超过 context 限制

**生命周期**:
- 调用者确保 backendRenderTarget 在 SkSurface 生命周期内有效
- releaseProc 在可安全删除时调用

### 获取后端资源

#### `GetBackendTexture`
```cpp
SK_API GrBackendTexture GetBackendTexture(
    SkSurface* surface,
    BackendHandleAccess access);
```

**功能**: 从 SkSurface 获取底层后端纹理

**参数**:
- `surface`: SkSurface 指针
- `access`: 后端句柄访问模式

**返回值**: GrBackendTexture,无效时调用 isValid() 返回 false

**注意事项**:
- 如果 SkSurface 被绘制或删除,返回的 GrBackendTexture 应丢弃
- 不是所有 SkSurface 都有后端纹理

#### `GetBackendRenderTarget`
```cpp
SK_API GrBackendRenderTarget GetBackendRenderTarget(
    SkSurface* surface,
    BackendHandleAccess access);
```

**功能**: 从 SkSurface 获取底层后端渲染目标

**返回值**: GrBackendRenderTarget,无效时调用 isValid() 返回 false

**失效条件**: SkSurface 被绘制或删除后

### MSAA Resolve

#### `ResolveMSAA`
```cpp
SK_API void ResolveMSAA(SkSurface* surface);
```

**功能**: 插入 MSAA resolve 命令到 GPU 命令流

**前提条件**:
- SkSurface 是 Ganesh 后端
- 使用 MSAA 渲染
- 存在 resolve 纹理

**应用场景**:
- 包装单采样纹理但使用 MSAA 渲染时
- 需要在 Skia 外部使用包装的纹理
- 触发 resolve 的方式: 调用此函数或 GrDirectContext::flush

**注意**:
- 需要后续 flush 和 submit 才能实际执行
- 无脏数据或不支持 resolve 时为空操作

**重载版本**:
```cpp
inline void ResolveMSAA(const sk_sp<SkSurface>& surface);
```

## 辅助函数 (skgpu::ganesh 命名空间)

### `Flush`
```cpp
SK_API GrSemaphoresSubmitted Flush(sk_sp<SkSurface>);
SK_API GrSemaphoresSubmitted Flush(SkSurface*);
```

**功能**: 刷新 SkSurface 的 GPU 命令

**建议**: 应尽量直接调用 GrDirectContext::flush

**返回值**: GrSemaphoresSubmitted - 指示信号量是否已提交

**空操作条件**:
- surface 为 nullptr
- surface 不是 GPU 后端

### `FlushAndSubmit`
```cpp
SK_API void FlushAndSubmit(sk_sp<SkSurface>);
SK_API void FlushAndSubmit(SkSurface*);
```

**功能**: 刷新并提交 SkSurface 的 GPU 命令到 GPU

**区别于 Flush**: 额外执行 submit 操作,确保命令发送到 GPU

## 内部实现细节

### MSAA 渲染流程
1. 创建 MSAA 渲染目标(sampleCnt > 0)
2. 渲染到 MSAA 表面
3. Resolve 到单采样纹理/渲染目标
4. 最终图像在单采样纹理中

### 预算管理
- kYes: 资源可被缓存系统驱逐
- kNo: 资源保留直到显式释放
- 影响 GPU 内存压力时的资源回收策略

### DDL 兼容性
通过 GrSurfaceCharacterization 创建的表面:
- 保证与 DDL 录制的特征匹配
- 支持延迟渲染工作流

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkSurface.h | 表面抽象基类 |
| include/core/SkImageInfo.h | 图像信息描述 |
| GrRecordingContext | GPU 命令录制上下文 |
| GrBackendTexture | 后端纹理抽象 |
| GrBackendRenderTarget | 后端渲染目标抽象 |
| GrSurfaceCharacterization | 表面特征描述 |
| GrTypes.h | Ganesh 核心类型 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkCanvas | 在 Surface 上绘制 |
| 窗口系统集成 | 创建屏幕渲染目标 |
| 离屏渲染 | 纹理烘焙、特效合成 |
| DDL 录制 | 延迟显示列表 |

## 设计模式与设计决策

### 工厂函数模式
使用独立工厂函数而非类静态方法:
- 清晰的命名空间组织
- 支持函数重载
- 避免 SkSurface 类膨胀

### 资源管理策略
- RAII: sk_sp 自动管理引用计数
- 回调: 通知外部资源释放时机
- 预算: 允许 GPU 内存压力时回收

### 向后兼容性
提供多个重载版本,逐步简化参数:
- 完整版本支持所有参数
- 简化版本使用合理默认值

## 性能考量

### MSAA 开销
- 采样数越高,内存和带宽开销越大
- Resolve 操作消耗 GPU 周期
- 移动设备考虑使用较低采样数(2x/4x)

### Mipmap 生成
- shouldCreateWithMips 仅为提示
- 实际生成取决于 GPU 支持和图像使用模式
- 影响 makeImageSnapshot 性能

### 预算控制
- Budgeted::kYes 允许缓存复用,提升性能
- Budgeted::kNo 适用于临时渲染目标
- 平衡内存使用和创建开销

## 平台相关说明

### Vulkan 特定
- isProtected 参数启用受保护内存
- 需要 Vulkan 扩展支持
- 受保护表面不能与非保护上下文混用

### OpenGL 特定
- 默认方向 kBottomLeft 符合 GL 传统
- MSAA 通过 FBO 多重采样实现
- Resolve 使用 glBlitFramebuffer

### Metal 特定
- 使用 MTLTexture 和 MTLRenderTarget
- MSAA resolve 通过 store action
- 支持 iOS 的 tile-based rendering 优化

### Direct3D 特定
- 使用 ID3D12Resource
- MSAA resolve 通过 ResolveSubresource
- 受保护资源通过 D3D12 受保护会话

## 相关文件
| 文件 | 关系 |
|------|------|
| include/core/SkSurface.h | 基类定义 |
| include/gpu/ganesh/GrBackendSurface.h | 后端资源类型 |
| src/gpu/ganesh/SkSurface_Ganesh.cpp | 实现文件 |
| include/gpu/ganesh/SkImageGanesh.h | Image 对应 API |
| include/gpu/ganesh/GrDirectContext.h | GPU 上下文 |
| src/gpu/ganesh/GrSurfaceCharacterization.h | 表面特征 |
