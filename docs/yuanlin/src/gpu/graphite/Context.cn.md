# Context (Graphite)

> 源文件
> - include/gpu/graphite/Context.h
> - src/gpu/graphite/Context.cpp

## 概述

`Context` 是 Skia Graphite GPU 渲染系统的核心管理对象，负责 GPU 资源管理、命令提交、异步操作和渲染录制器（Recorder）的创建。它是客户端与 GPU 硬件交互的主要接口，管理着整个渲染管线的生命周期。

与 Ganesh 的 `GrDirectContext` 类似，但 Graphite 的 `Context` 采用了更现代的设计理念，支持延迟命令录制、异步资源操作和更细粒度的资源控制。Context 对象是线程绑定的（通过 `SingleOwner` 保护），但可以创建多个 Recorder 在不同线程上录制命令。

## 架构位置

`Context` 位于 Graphite 渲染架构的最顶层：

- **上层**：客户端应用直接使用的 API 入口
- **同层**：与 `Recorder` 协作，Context 负责资源和提交，Recorder 负责命令录制
- **下层**：管理 `SharedContext`、`QueueManager`、`ResourceProvider` 等核心组件
- **所属模块**：`gpu/graphite` - Graphite 新一代 GPU 后端

Context 是单例化的管理对象，采用引用计数方式生命周期管理。

## 主要类与结构体

### Context 类

**继承关系**：
- 无继承，独立实现
- 不可复制、不可移动（删除拷贝/移动构造和赋值运算符）

**关键成员变量**：
| 成员变量 | 类型 | 用途 |
|---------|------|------|
| `fSharedContext` | `sk_sp<SharedContext>` | 共享的后端上下文（跨 Context/Recorder 共享） |
| `fResourceProvider` | `std::unique_ptr<ResourceProvider>` | 资源提供者，管理 GPU 资源 |
| `fQueueManager` | `std::unique_ptr<QueueManager>` | 队列管理器，负责 GPU 命令提交 |
| `fMappedBufferManager` | `std::unique_ptr<ClientMappedBufferManager>` | 客户端映射缓冲区管理 |
| `fCPUContext` | `std::unique_ptr<skcpu::ContextImpl>` | CPU 上下文实现 |
| `fContextID` | `ContextID` | 唯一的 Context 标识符 |
| `fSingleOwner` | `mutable SingleOwner` | 线程安全守护 |

### ContextID 嵌套类

用于唯一标识 Context 实例的轻量级 ID 类。

**关键成员**：
| 成员 | 类型 | 用途 |
|-----|------|------|
| `fID` | `uint32_t` | 内部 ID 值 |

**方法**：
- `Next()`：生成下一个唯一 ID（线程安全）
- `isValid()`：检查 ID 是否有效
- `makeInvalid()`：将 ID 标记为无效

## 公共 API 函数

### 核心管理函数

```cpp
BackendApi backend() const
```
返回当前 Context 使用的后端 API 类型（Vulkan、Metal、Dawn 等）。

```cpp
std::unique_ptr<Recorder> makeRecorder(const RecorderOptions& = {})
```
创建一个新的 Recorder 用于录制渲染命令。Recorder 可以在不同线程上使用。

```cpp
std::unique_ptr<skcpu::Recorder> makeCPURecorder()
```
创建 CPU Recorder 用于 CPU 端渲染操作。

```cpp
std::unique_ptr<PrecompileContext> makePrecompileContext()
```
创建预编译上下文，可在后台线程预编译着色器管线。

### 命令提交函数

```cpp
InsertStatus insertRecording(const InsertRecordingInfo&)
```
将录制好的 Recording 插入到提交队列中。

```cpp
bool submit(SubmitInfo submitInfo = {})
```
将所有待提交的命令提交到 GPU 执行。

**参数**：
- `submitInfo.fSync`：是否同步等待 GPU 完成

**返回值**：提交是否成功。

```cpp
bool hasUnfinishedGpuWork() const
```
检查是否有未完成的 GPU 工作。

```cpp
bool hasPendingGPUWork() const
```
检查是否有待提交的 GPU 工作。

### 异步像素读取函数

```cpp
void asyncRescaleAndReadPixels(const SkImage* src,
                               const SkImageInfo& dstImageInfo,
                               const SkIRect& srcRect,
                               SkImage::RescaleGamma rescaleGamma,
                               SkImage::RescaleMode rescaleMode,
                               SkImage::ReadPixelsCallback callback,
                               SkImage::ReadPixelsContext context)
```

**功能**：异步读取像素数据并支持缩放和颜色空间转换。

**特性**：
- 支持从 SkImage 或 SkSurface 读取
- 可选的缩放操作（使用不同质量模式）
- 线性/sRGB 伽马校正
- 异步回调机制避免阻塞主线程

```cpp
void asyncRescaleAndReadPixelsYUV420(const SkImage* src,
                                     SkYUVColorSpace yuvColorSpace,
                                     sk_sp<SkColorSpace> dstColorSpace,
                                     const SkIRect& srcRect,
                                     const SkISize& dstSize,
                                     SkImage::RescaleGamma rescaleGamma,
                                     SkImage::RescaleMode rescaleMode,
                                     SkImage::ReadPixelsCallback callback,
                                     SkImage::ReadPixelsContext context)
```

**功能**：异步读取像素并转换为 YUV420 平面格式（视频编码常用）。

**输出格式**：3 个平面（Y、U、V），U 和 V 是半分辨率。

```cpp
void asyncRescaleAndReadPixelsYUVA420(...)
```

**功能**：与 YUV420 类似，但额外返回全分辨率的 Alpha 平面（4 个平面）。

### 资源管理函数

```cpp
void deleteBackendTexture(const BackendTexture&)
```
删除通过 Recorder 创建的后端纹理。

```cpp
void freeGpuResources()
```
释放 GPU 资源（不包括正在使用的资源）。

```cpp
void performDeferredCleanup(std::chrono::milliseconds msNotUsed)
```
清理指定时间内未使用的资源。

```cpp
size_t currentBudgetedBytes() const
```
返回当前使用的 GPU 内存字节数。

```cpp
size_t maxBudgetedBytes() const
```
返回 GPU 内存预算上限。

```cpp
void setMaxBudgetedBytes(size_t bytes)
```
设置 GPU 内存预算，超出时会尝试释放资源。

### 其他功能

```cpp
void checkAsyncWorkCompletion()
```
检查异步工作完成状态并触发相关回调。

```cpp
bool isDeviceLost() const
```
检查 GPU 设备是否丢失（如驱动崩溃）。

```cpp
int maxTextureSize() const
```
返回最大纹理尺寸限制。

```cpp
void syncPipelineData(size_t maxSize = SIZE_MAX)
```
同步管线缓存数据到持久化存储。

```cpp
void startCapture() / sk_sp<SkCapture> endCapture()
```
启动/结束渲染捕获（用于调试和分析）。

## 内部实现细节

### 初始化流程

1. **构造函数**：
   - 初始化 SharedContext 和 QueueManager
   - 加载 Graphite SkSL 模块（使用 `SkOnce` 确保只加载一次）
   - 创建 ResourceProvider（带预算控制）
   - 初始化 ClientMappedBufferManager
   - 设置管线缓存回调

2. **finishInitialization()**：
   - 初始化动态采样器
   - 创建 RendererProvider
   - 填充静态顶点缓冲区
   - 提交初始命令缓冲区

### 异步读取实现

#### 核心结构 PixelTransferResult

```cpp
struct PixelTransferResult {
    sk_sp<Buffer> fTransferBuffer;  // 传输缓冲区
    SkISize fSize;                  // 数据尺寸
    size_t fRowBytes;               // 行字节数
    std::function<ConversionFn> fPixelConverter;  // 像素转换函数
};
```

#### 读取流程

1. **验证参数**：检查源图像、矩形区域、目标格式有效性
2. **判断是否需要缩放**：
   - 尺寸相同：直接读取
   - 尺寸不同：先缩放到目标尺寸
3. **处理不可读纹理**：使用 `CopyAsDraw` 绘制到可读格式
4. **创建传输缓冲区**：使用 `transferPixels` 创建 GPU->CPU 传输任务
5. **添加任务到队列**：通过 Recorder 或直接添加到 QueueManager
6. **注册完成回调**：GPU 完成后映射缓冲区并调用客户端回调

#### YUV420 转换

使用颜色矩阵分别提取 Y、U、V 平面：
- Y 平面：全分辨率，存储亮度信息
- U/V 平面：半分辨率（4:2:0 采样）
- 每个平面通过绘制到 A8 Surface 并应用颜色矩阵提取

### 资源缓存策略

- 使用预算机制限制 GPU 内存使用
- 支持手动和自动资源清理
- 跟踪资源使用时间，支持 LRU 清理
- 区分可清除资源和锁定资源

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SharedContext` | 共享的后端配置和能力查询 |
| `QueueManager` | 管理 GPU 命令队列和提交 |
| `ResourceProvider` | 创建和管理 GPU 资源 |
| `ClientMappedBufferManager` | 管理客户端可访问的缓冲区 |
| `Recorder` | 录制渲染命令 |
| `Recording` | 封装录制好的命令序列 |
| `TextureProxy` | 纹理代理对象 |
| `Buffer` | GPU 缓冲区对象 |
| `Caps` | 后端能力查询 |
| `RendererProvider` | 提供渲染器实现 |
| `AtlasProvider` | 图集管理 |

### 被依赖的模块

- **客户端应用**：创建 Context 初始化 Graphite 渲染环境
- **Recorder**：通过 Context 创建，共享资源提供者
- **Surface**：使用 Context 进行渲染操作
- **Image**：异步读取操作需要 Context

## 设计模式与设计决策

### 单所有者模式

使用 `SingleOwner` 确保线程安全：
- Context 绑定到创建它的线程
- 所有公共 API 都检查 `ASSERT_SINGLE_OWNER`
- 避免多线程竞争，简化实现

### 资源提供者共享

- Context 拥有 ResourceProvider
- 通过 Context 创建的内部 Recorder 共享 ResourceProvider
- 客户端 Recorder 拥有独立的 ResourceProvider（独立预算）

### 异步操作设计

- 所有像素读取都是异步的
- 使用回调机制避免阻塞
- 支持多种读取模式（直接读、缩放、格式转换）
- 自动处理 GPU 同步和缓冲区映射

### 延迟命令录制

- Context 本身不直接录制命令
- 通过 Recorder 录制，生成 Recording
- Recording 提交到 Context 执行
- 支持多线程并行录制

## 性能考量

### 命令批处理

- Recording 可以累积多个 Recorder 的命令
- 一次 submit 提交多个 Recording
- 减少 GPU 命令队列切换开销

### 异步操作优化

- 像素读取使用传输缓冲区而非同步映射
- 支持异步缓冲区映射（某些后端）
- 回调在 GPU 完成后才执行，避免阻塞

### 资源复用

- 传输缓冲区由 Context 管理，可复用
- 着色器缓存跨 Recorder 共享
- 图集资源在有序 Recording 模式下跨帧复用

### 内存管理

- 基于预算的资源缓存
- 支持按时间清理未使用资源
- 区分客户端和内部 Recorder 的内存预算

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/gpu/graphite/Recorder.h` | Recorder 定义，用于录制命令 |
| `include/gpu/graphite/Recording.h` | Recording 定义，封装录制结果 |
| `include/gpu/graphite/ContextOptions.h` | Context 配置选项 |
| `src/gpu/graphite/SharedContext.h` | 共享上下文实现 |
| `src/gpu/graphite/QueueManager.h` | 队列管理器 |
| `src/gpu/graphite/ResourceProvider.h` | 资源提供者 |
| `src/gpu/graphite/ContextPriv.h` | Context 内部接口 |
| `src/gpu/graphite/TextureUtils.h` | 纹理工具函数 |
| `src/gpu/graphite/task/CopyTask.h` | 复制任务实现 |
