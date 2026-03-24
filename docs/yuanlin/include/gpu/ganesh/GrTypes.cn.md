# GrTypes

> 源文件: `include/gpu/ganesh/GrTypes.h`

## 概述
GrTypes 是 Ganesh GPU 后端的核心类型定义文件,提供了 GPU API 抽象、表面属性、同步机制和回调接口的基础类型。该文件定义了跨平台 GPU 编程所需的枚举、结构体和函数指针类型,是 Ganesh 架构中最基础的头文件之一。

## 架构位置
该文件位于 Ganesh 公共 API 的最底层,被几乎所有 Ganesh 模块依赖。它桥接了平台无关的 Skia API 和具体的 GPU 后端实现(OpenGL, Vulkan, Metal, Direct3D),为上层提供统一的类型系统。

## 核心枚举类型

### GrBackendApi
```cpp
enum class GrBackendApi : unsigned {
    kOpenGL,
    kVulkan,
    kMetal,
    kDirect3D,
    kMock,
    kUnsupported,
    kOpenGL_GrBackend = kOpenGL,  // 向后兼容
};
```
- **功能**: 标识 Ganesh 支持的 GPU 后端 API 类型
- **平台映射**:
  - `kOpenGL`: OpenGL/OpenGL ES/WebGL
  - `kVulkan`: Vulkan API
  - `kMetal`: Apple Metal
  - `kDirect3D`: Microsoft Direct3D 12
  - `kMock`: 单元测试用空后端,测量 CPU 开销
  - `kUnsupported`: 不支持的后端(如 Dawn)
- **向后兼容**: 保留 `kOpenGL_GrBackend` 等旧名称

### GrBackend (typedef)
```cpp
typedef GrBackendApi GrBackend;
```
- **用途**: 旧版本 API 兼容性
- **废弃**: 新代码应使用 GrBackendApi

### 向后兼容常量
```cpp
static constexpr GrBackendApi kMetal_GrBackend = GrBackendApi::kMetal;
static constexpr GrBackendApi kVulkan_GrBackend = GrBackendApi::kVulkan;
static constexpr GrBackendApi kMock_GrBackend = GrBackendApi::kMock;
```

## 表面属性类型

### GrRenderable
```cpp
using GrRenderable = skgpu::Renderable;
```
- **功能**: 标识 GrBackendObject 是否可作为渲染目标
- **来源**: 从 skgpu 命名空间复用通用 GPU 类型
- **可能值**: kYes, kNo

### GrProtected
```cpp
using GrProtected = skgpu::Protected;
```
- **功能**: 标识纹理是否由受保护内存支持(DRM 内容保护)
- **平台支持**: 主要用于 Vulkan 和 Direct3D
- **可能值**: kYes, kNo

### GrSurfaceOrigin
```cpp
enum GrSurfaceOrigin : int {
    kTopLeft_GrSurfaceOrigin,
    kBottomLeft_GrSurfaceOrigin,
};
```
- **功能**: 定义纹理坐标系统原点
- **影响**:
  - `kTopLeft`: (0,0) 对应左上角像素
  - `kBottomLeft`: (0,0) 对应左下角像素(OpenGL 传统)
- **应用**: GPU SkImage 和 SkSurface 的纹理方向

## OpenGL 状态管理

### GrGLBackendState
```cpp
enum GrGLBackendState {
    kRenderTarget_GrGLBackendState     = 1 << 0,
    kTextureBinding_GrGLBackendState   = 1 << 1,  // 包括采样器绑定
    kView_GrGLBackendState             = 1 << 2,  // 视口和裁剪
    kBlend_GrGLBackendState            = 1 << 3,
    kMSAAEnable_GrGLBackendState       = 1 << 4,
    kVertex_GrGLBackendState           = 1 << 5,
    kStencil_GrGLBackendState          = 1 << 6,
    kPixelStore_GrGLBackendState       = 1 << 7,
    kProgram_GrGLBackendState          = 1 << 8,
    kFixedFunction_GrGLBackendState    = 1 << 9,
    kMisc_GrGLBackendState             = 1 << 10,
    kALL_GrGLBackendState              = 0xffff
};
```
- **功能**: 位掩码标识哪些 OpenGL 状态可能失效
- **应用场景**: 当外部代码修改 GL 状态后,通知 Ganesh 重新验证
- **组合使用**: 可通过位或运算组合多个状态位

### kAll_GrBackendState
```cpp
static const uint32_t kAll_GrBackendState = 0xffffffff;
```
- **功能**: 通用常量,重置所有后端状态(不限于 GL)
- **应用**: 在上下文切换或外部 GPU 操作后使用

## 回调函数类型

### GPU 完成回调
```cpp
typedef void* GrGpuFinishedContext;
typedef void (*GrGpuFinishedProc)(GrGpuFinishedContext finishedContext);
typedef void (*GrGpuFinishedWithStatsProc)(GrGpuFinishedContext finishedContext,
                                           const skgpu::GpuStats&);
```
- **GrGpuFinishedProc**: 当 GPU 工作完成时调用
- **GrGpuFinishedWithStatsProc**: 完成时提供 GPU 统计信息
- **上下文传递**: GrGpuFinishedContext 可携带用户自定义数据
- **优先级**: 如果两者都提供,优先使用 WithStatsProc

### GPU 提交回调
```cpp
typedef void* GrGpuSubmittedContext;
typedef void (*GrGpuSubmittedProc)(GrGpuSubmittedContext submittedContext, bool success);
```
- **功能**: 当工作提交到 GPU 时调用(不等待完成)
- **success 参数**: 指示提交是否成功
- **应用场景**: 信号量管理,判断何时可等待或删除信号量
- **失败处理**: 提交失败时立即调用,不会重试

### 上下文销毁回调
```cpp
typedef void* GrDirectContextDestroyedContext;
typedef void (*GrDirectContextDestroyedProc)(GrDirectContextDestroyedContext destroyedContext);
```
- **功能**: 当 GrDirectContext 被销毁时通知
- **应用**: 资源清理,外部对象生命周期管理

## 核心结构体

### GrFlushInfo
```cpp
struct GrFlushInfo {
    size_t fNumSemaphores = 0;
    skgpu::GpuStatsFlags fGpuStatsFlags = skgpu::GpuStatsFlags::kNone;
    GrBackendSemaphore* fSignalSemaphores = nullptr;
    GrGpuFinishedProc fFinishedProc = nullptr;
    GrGpuFinishedWithStatsProc fFinishedWithStatsProc = nullptr;
    GrGpuFinishedContext fFinishedContext = nullptr;
    GrGpuSubmittedProc fSubmittedProc = nullptr;
    GrGpuSubmittedContext fSubmittedContext = nullptr;
};
```

**成员说明**:

| 成员 | 类型 | 说明 |
|------|------|------|
| fNumSemaphores | size_t | 信号量数量 |
| fGpuStatsFlags | skgpu::GpuStatsFlags | 请求的统计信息类型 |
| fSignalSemaphores | GrBackendSemaphore* | 要发出信号的信号量数组 |
| fFinishedProc | 函数指针 | GPU 完成回调(无统计) |
| fFinishedWithStatsProc | 函数指针 | GPU 完成回调(带统计) |
| fFinishedContext | void* | 完成回调上下文 |
| fSubmittedProc | 函数指针 | GPU 提交回调 |
| fSubmittedContext | void* | 提交回调上下文 |

**关键行为**:
1. **信号量生命周期**:
   - 信号量在 flush 调用中初始化或传入已初始化对象
   - 实际发送到 GPU 需等待下一次 GrContext::submit
   - 客户端拥有并负责删除底层信号量
   - GrBackendSemaphore 对象本身可在函数返回后立即删除

2. **回调时机**:
   - fSubmittedProc: flush 工作提交到 GPU 时调用
   - fFinishedProc: 所有历史工作(包括之前的 flush)完成后调用
   - 失败时立即调用回调

3. **统计信息**:
   - 通过 fGpuStatsFlags 请求特定统计项
   - 仅当 fFinishedWithStatsProc 被调用时有效
   - 取决于后端支持

**平台限制**:
- OpenGL 后端忽略信号量

### GrSemaphoresSubmitted
```cpp
enum class GrSemaphoresSubmitted : bool {
    kNo = false,
    kYes = true
};
```
- **功能**: flush 返回值,指示信号量是否会在下次 submit 时发送
- **应用**: 客户端据此决定是否等待信号量

### GrPurgeResourceOptions
```cpp
enum class GrPurgeResourceOptions {
    kAllResources,
    kScratchResourcesOnly,
};
```
- **功能**: 控制资源清除策略
- **kAllResources**: 清除所有未使用资源
- **kScratchResourcesOnly**: 仅清除临时资源

### GrSyncCpu
```cpp
enum class GrSyncCpu : bool {
    kNo = false,
    kYes = true,
};
```
- **功能**: 是否在 submit 后同步等待 GPU 完成

### GrMarkFrameBoundary
```cpp
enum class GrMarkFrameBoundary : bool {
    kNo = false,
    kYes = true,
};
```
- **功能**: 是否标记帧边界用于性能分析和优化

### GrSubmitInfo
```cpp
struct GrSubmitInfo {
    GrSyncCpu fSync = GrSyncCpu::kNo;
    GrMarkFrameBoundary fMarkBoundary = GrMarkFrameBoundary::kNo;
    uint64_t fFrameID = 0;
};
```

**成员说明**:
| 成员 | 类型 | 说明 |
|------|------|------|
| fSync | GrSyncCpu | 是否 CPU 同步等待 |
| fMarkBoundary | GrMarkFrameBoundary | 是否标记帧边界 |
| fFrameID | uint64_t | 帧 ID,用于跟踪和调试 |

**应用场景**:
- 性能分析工具(如 GPU 调试器)使用 fFrameID
- fMarkBoundary 帮助驱动程序优化命令批次
- fSync 用于测试或需要精确同步的场景

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/core/SkTypes.h | Skia 核心类型定义 |
| include/gpu/GpuTypes.h | 通用 GPU 类型(skgpu 命名空间) |
| include/private/base/SkTo.h | 类型安全转换工具 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| GrContext | 使用回调和刷新类型 |
| GrBackendSurface | 使用表面属性枚举 |
| GrGpu | 使用后端 API 枚举 |
| GrCaps | 查询后端能力 |
| 所有 Ganesh 头文件 | 基础类型依赖 |

## 设计模式与设计决策

### 类型别名统一
通过 `using` 将 skgpu 通用类型引入 Ganesh 命名空间,实现:
- API 一致性:客户端代码使用统一的 Gr 前缀
- 代码复用:底层实现共享 skgpu 通用代码
- 平滑迁移:逐步将代码移至 skgpu 统一命名空间

### 向后兼容策略
保留旧版枚举名称和 typedef:
```cpp
typedef GrBackendApi GrBackend;  // 旧名称
static constexpr GrBackendApi kMetal_GrBackend = GrBackendApi::kMetal;
```
允许渐进式 API 升级,不破坏现有代码

### 回调函数设计
采用 C 风格函数指针 + void* 上下文:
- 兼容 C 接口
- 避免 std::function 的开销
- 支持跨 DLL 边界传递

### 位掩码状态管理
GrGLBackendState 使用位标志允许:
- 高效的状态组合(位或运算)
- 快速状态检查(位与运算)
- 最小的内存占用

## 性能考量

### 信号量开销
- 信号量创建和同步有性能成本
- 仅在必要时使用(如跨 API 同步)
- GL 后端完全跳过信号量操作

### 回调时机优化
- fSubmittedProc 在提交时立即调用,适合轻量操作
- fFinishedProc 在 GPU 完成后调用,可能有较大延迟
- 避免在回调中执行耗时操作

### 同步策略
- GrSyncCpu::kYes 强制 CPU 等待,降低并行性
- 仅在需要精确同步时使用(如测试或截图)
- 正常渲染应避免同步,依赖异步完成回调

## 平台相关说明

### OpenGL 特定
- GrGLBackendState 仅用于 GL 后端
- 信号量在 GL 后端被忽略(文档明确说明)
- 固定功能管线状态在现代 GL 可能不适用

### Vulkan 特定
- 信号量是原生支持的核心同步机制
- 受保护内存(GrProtected)主要用于 Vulkan
- 帧边界标记对 Vulkan 性能优化重要

### Metal 特定
- 使用 MTLEvent 实现信号量语义
- 帧 ID 可映射到 Metal 的帧捕获工具

### Direct3D 特定
- 使用 ID3D12Fence 实现信号量
- 受保护资源通过 D3D12 受保护资源会话

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/GpuTypes.h | 通用 GPU 类型定义 |
| include/gpu/ganesh/GrBackendSemaphore.h | 信号量封装 |
| include/gpu/ganesh/GrDirectContext.h | 使用刷新和提交类型 |
| src/gpu/ganesh/GrCaps.h | 后端能力查询 |
| src/gpu/ganesh/gl/GrGLGpu.h | OpenGL 后端实现 |
