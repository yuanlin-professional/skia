# Recorder

> 源文件
> - include/gpu/graphite/Recorder.h
> - src/gpu/graphite/Recorder.cpp

## 概述

`Recorder` 是 Skia Graphite 渲染系统中负责录制渲染命令的核心对象。它实现了延迟命令录制（Deferred Recording）模式，允许在多个线程上并行录制渲染命令，最后通过 `Context` 统一提交到 GPU。

Recorder 的主要职责包括：
- 录制绘制命令到内部任务列表
- 管理录制期间的临时资源（缓冲区、纹理、图集等）
- 追踪设备（Device）并在需要时刷新其命令
- 创建和更新后端纹理
- 生成可提交的 Recording 对象

与 Ganesh 的 `GrRecordingContext` 相比，Graphite 的 Recorder 更轻量、线程局部性更强，且支持更细粒度的资源控制。

## 架构位置

`Recorder` 位于 Graphite 渲染架构的命令录制层：

- **上层**：被 SkCanvas、SkSurface 通过 Device 使用
- **同层**：与 Context 协作，Recorder 录制命令，Context 管理提交
- **下层**：管理 DrawBufferManager、UploadBufferManager、AtlasProvider 等
- **所属模块**：`gpu/graphite` - 命令录制和资源管理

Recorder 是多线程友好的，每个线程可以拥有独立的 Recorder。

## 主要类与结构体

### Recorder 类

**继承关系**：
```cpp
class Recorder final : public SkRecorder
```
- 继承自 `SkRecorder`（Skia 录制器抽象基类）
- 不可复制、不可移动

**关键成员变量**：

| 成员变量 | 类型 | 用途 |
|---------|------|------|
| `fSharedContext` | `sk_sp<SharedContext>` | 共享的后端上下文 |
| `fResourceProvider` | `ResourceProvider*` | 资源提供者（可能共享） |
| `fOwnedResourceProvider` | `std::unique_ptr<ResourceProvider>` | 自有资源提供者（独立预算） |
| `fRuntimeEffectDict` | `sk_sp<RuntimeEffectDictionary>` | 运行时效果字典 |
| `fRootTaskList` | `std::unique_ptr<TaskList>` | 根任务列表 |
| `fRootUploads` | `std::unique_ptr<UploadList>` | 根上传列表 |
| `fDrawBufferManager` | `std::unique_ptr<DrawBufferManager>` | 绘制缓冲区管理 |
| `fUploadBufferManager` | `std::unique_ptr<UploadBufferManager>` | 上传缓冲区管理 |
| `fTrackedDevices` | `skia_private::TArray<sk_sp<Device>>` | 追踪的设备列表 |
| `fAtlasProvider` | `std::unique_ptr<AtlasProvider>` | 图集提供者 |
| `fStrikeCache` | `std::unique_ptr<sktext::gpu::StrikeCache>` | 字形缓存 |
| `fTextBlobCache` | `std::unique_ptr<sktext::gpu::TextBlobRedrawCoordinator>` | 文本 Blob 缓存 |
| `fUniqueID` | `uint32_t` | 唯一标识符 |
| `fRequireOrderedRecordings` | `const bool` | 是否要求有序录制 |

### RecorderOptions 结构体

配置 Recorder 创建的选项。

**关键成员**：
| 成员 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| `fImageProvider` | `sk_sp<ImageProvider>` | 默认提供者 | 自定义图像转换器 |
| `fGpuBudgetInBytes` | `size_t` | 256MB | GPU 资源预算 |
| `fRequireOrderedRecordings` | `std::optional<bool>` | 后端决定 | 是否要求有序录制 |

### KeyAndDataBuilder 类型别名

```cpp
using KeyAndDataBuilder = std::pair<PipelineDataGatherer, PaintParamsKeyBuilder>;
```
用于构建管线键和数据的工具对。

## 公共 API 函数

### 基础查询

```cpp
BackendApi backend() const
```
返回使用的后端 API 类型。

```cpp
Type type() const override
```
返回 `SkRecorder::Type::kGraphite`。

```cpp
int maxTextureSize() const
```
返回最大纹理尺寸限制。

### 录制管理

```cpp
std::unique_ptr<Recording> snap()
```

**功能**：完成当前录制，生成可提交的 Recording 对象。

**流程**：
1. 刷新所有追踪的设备，收集待提交的命令
2. 完成缓冲区管理器的数据传输
3. 将上传任务和绘制任务添加到 Recording
4. 调用 `prepareResources` 准备 GPU 资源
5. 重置内部状态，为下次录制做准备

**返回值**：
- 成功：包含所有命令的 Recording
- 失败：nullptr（通常是资源准备失败）

**注意**：snap 后，之前的 Canvas 和 Device 将失效。

```cpp
SkCanvas* makeDeferredCanvas(const SkImageInfo&, const TextureInfo&)
```

**功能**：创建延迟 Canvas，渲染到代理纹理（延迟绑定实际纹理）。

**使用场景**：
- 需要在不知道最终纹理的情况下录制命令
- 支持纹理延迟绑定（Lazy Texture Binding）

**限制**：
- 每次只能有一个延迟 Canvas 活跃
- 必须在 snap 前完成绘制

### 纹理管理

```cpp
BackendTexture createBackendTexture(SkISize dimensions, const TextureInfo&)
```

**功能**：创建后端 GPU 纹理。

**参数**：
- `dimensions`：纹理尺寸
- `TextureInfo`：纹理格式、用途等配置

**返回值**：
- 成功：有效的 BackendTexture
- 失败：无效的 BackendTexture（调用 `isValid()` 检查）

**生命周期**：
- 创建者负责调用 `deleteBackendTexture` 释放
- 可在不同 Recorder 或 Context 上删除（需同一后端）

```cpp
bool updateBackendTexture(const BackendTexture&,
                          const SkPixmap srcData[],
                          int numLevels,
                          GpuFinishedProc = nullptr,
                          GpuFinishedContext = nullptr)
```

**功能**：更新后端纹理内容（支持 mipmap）。

**参数**：
- `srcData`：像素数据数组（每层一个 SkPixmap）
- `numLevels`：mip 层级数（必须与纹理一致）
- `finishedProc`：完成回调（GPU 安全删除纹理时调用）

**返回值**：更新是否成功。

**注意**：
- 需要调用 `Context::submit()` 才能执行上传
- Mipmap 纹理必须提供所有层级的数据
- 颜色类型必须与纹理格式兼容

```cpp
bool updateCompressedBackendTexture(const BackendTexture&,
                                    const void* data,
                                    size_t dataSize,
                                    GpuFinishedProc,
                                    GpuFinishedContext)
```

**功能**：更新压缩纹理（如 ETC、ASTC 等）。

```cpp
void deleteBackendTexture(const BackendTexture&)
```

**功能**：删除通过此 Recorder 创建的纹理。

### 完成回调

```cpp
void addFinishInfo(const InsertFinishInfo&)
```

**功能**：添加完成回调，在命令执行完成后触发。

**流程**：
- 回调添加到 Recording
- Recording 提交后，回调附加到 CommandBuffer
- GPU 完成工作后调用回调

### 资源管理

```cpp
void freeGpuResources()
```
释放 GPU 资源（不包括正在使用的）。

```cpp
void performDeferredCleanup(std::chrono::milliseconds msNotUsed)
```
清理指定时间未使用的资源。

```cpp
size_t currentBudgetedBytes() const
size_t currentPurgeableBytes() const
size_t maxBudgetedBytes() const
void setMaxBudgetedBytes(size_t bytes)
```
资源预算查询和设置。

```cpp
void dumpMemoryStatistics(SkTraceMemoryDump*) const
```
导出内存统计信息（用于调试）。

## 内部实现细节

### 构造流程

```cpp
Recorder::Recorder(sk_sp<SharedContext> sharedContext,
                   const RecorderOptions& options,
                   const Context* context)
```

**关键初始化**：
1. 决定是否共享 ResourceProvider：
   - 有 `context`：共享 Context 的 ResourceProvider（用于内部 Recorder）
   - 无 `context`：创建独立 ResourceProvider（客户端 Recorder）
2. 创建缓冲区管理器：
   - `DrawBufferManager`：管理顶点/索引/实例缓冲区
   - `UploadBufferManager`：管理纹理上传缓冲区
3. 初始化缓存：
   - `AtlasProvider`：图集管理（文本、路径等）
   - `StrikeCache`：字形缓存
   - `TextBlobRedrawCoordinator`：文本 Blob 缓存
4. 设置有序录制策略：
   - 优先使用用户指定
   - 否则根据后端能力决定

### 设备追踪机制

#### 注册设备

```cpp
void Recorder::registerDevice(sk_sp<Device> device)
```
将 Device 添加到追踪列表，防止在其他线程删除。

#### 注销设备

```cpp
void Recorder::deregisterDevice(const Device* device)
```
将列表中对应项置为 nullptr（延迟清理）。

#### 刷新设备

```cpp
void RecorderPriv::flushTrackedDevices(SK_DUMP_TASKS_CODE(const char* flushSource))
```

**流程**：
1. 遍历所有追踪的设备
2. 调用 `device->flushPendingWork()` 收集命令
3. 发布新的刷新令牌（Flush Token）
4. 清理无效和唯一引用的设备

**重入性**：
- 有 `dependency` 版本支持重入（特定纹理依赖刷新）
- 无参数版本不可重入（使用 `fIsFlushingTrackedDevices` 保护）

### 缓冲区管理

#### DrawBufferManager

管理绘制使用的缓冲区：
- **顶点缓冲区**：存储顶点数据
- **索引缓冲区**：存储索引数据
- **实例缓冲区**：存储实例数据（GPU Instancing）
- **Uniform 缓冲区**：存储着色器常量

**工作流程**：
1. 录制时分配缓冲区空间
2. snap 时调用 `transferToRecording` 生成传输任务
3. Recording 包含缓冲区绑定命令

#### UploadBufferManager

管理纹理上传缓冲区：
- **暂存缓冲区**（Staging Buffer）：CPU 可写，GPU 可读
- **传输优化**：批量上传多个纹理

**工作流程**：
1. 录制时分配上传空间并写入数据
2. snap 时生成 CopyBufferToTexture 任务
3. GPU 完成后自动释放缓冲区

### KeyAndDataBuilder 池化

```cpp
std::unique_ptr<KeyAndDataBuilder> RecorderPriv::popOrCreateKeyAndDataBuilder()
```

**设计目的**：
- 减少频繁分配销毁开销
- 复用内部缓冲区

**工作机制**：
- 池大小：`kMaxKeyAndDataBuilders = 2`
- pop 时优先从池中取
- push 时池未满则回收
- snap 时收缩容量（使用量 < 一半时）

### 任务提交流程

```cpp
void RecorderPriv::add(sk_sp<Task> task)
```

**任务类型**：
- **RenderPassTask**：渲染通道任务（绘制命令）
- **CopyTask**：资源复制任务
- **UploadTask**：纹理上传任务
- **SynchronizeTask**：同步任务

**任务树结构**：
```
Recording
├── UploadTask (fRootUploads)
└── TaskList (fRootTaskList)
    ├── RenderPassTask
    ├── CopyTask
    └── ...
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SharedContext` | 共享配置和全局缓存 |
| `ResourceProvider` | 创建 GPU 资源 |
| `DrawBufferManager` | 管理绘制缓冲区 |
| `UploadBufferManager` | 管理上传缓冲区 |
| `AtlasProvider` | 图集管理 |
| `Device` | 绘制设备（连接到 SkSurface） |
| `Recording` | 录制结果容器 |
| `TaskList` | 任务队列 |
| `RuntimeEffectDictionary` | 运行时效果字典 |

### 被依赖的模块

- **Context**：创建 Recorder
- **SkSurface**：通过 Device 使用 Recorder
- **SkCanvas**：间接通过 Device 录制命令

## 设计模式与设计决策

### 延迟录制模式

**优势**：
- 多线程并行录制
- 减少 GPU 阻塞
- 支持命令重排优化

**实现**：
- 录制期间仅生成任务描述
- snap 时统一准备资源
- Context 提交时才执行 GPU 命令

### 资源所有权模型

**客户端 Recorder**（无 context 参数）：
- 独立 ResourceProvider
- 独立内存预算
- 生命周期由客户端控制

**内部 Recorder**（有 context 参数）：
- 共享 Context 的 ResourceProvider
- 无独立预算
- 短生命周期（API 调用内部使用）

### 设备追踪机制

**设计目的**：
- 安全处理 Surface/Device 销毁
- 支持跨线程删除
- 自动刷新依赖

**实现细节**：
- 强引用防止意外删除
- 延迟清理避免遍历冲突
- flush 时清理无效项

### 有序录制策略

**有序模式**（fRequireOrderedRecordings = true）：
- Recording 按录制顺序提交
- 图集可跨帧复用
- 适合固定渲染流程（UI、文本）

**无序模式**（fRequireOrderedRecordings = false）：
- Recording 可乱序提交
- 图集每帧重建
- 适合动态场景（游戏）

## 性能考量

### 多线程录制

**最佳实践**：
- 每个线程一个 Recorder
- 避免共享 Device
- 统一通过 Context 提交

### 缓冲区复用

- DrawBufferManager 使用环形缓冲区
- UploadBufferManager 批量分配
- 减少内存碎片

### 图集优化

**有序模式**：
- 图集跨帧复用
- 减少重新上传
- 降低内存带宽

**无序模式**：
- 图集每帧重建
- 更大初始容量
- 避免扩容

### 命令批处理

- 相同状态的绘制合并
- 减少状态切换
- 提高 GPU 利用率

### 内存管理

- 基于预算的资源缓存
- 按时间清理未使用资源
- 区分可清除和锁定资源

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/gpu/graphite/Context.h` | Context 定义 |
| `include/gpu/graphite/Recording.h` | Recording 定义 |
| `include/core/SkCanvas.h` | Canvas 定义 |
| `include/core/SkSurface.h` | Surface 定义 |
| `src/gpu/graphite/Device.h` | Device 实现 |
| `src/gpu/graphite/DrawBufferManager.h` | 绘制缓冲区管理 |
| `src/gpu/graphite/UploadBufferManager.h` | 上传缓冲区管理 |
| `src/gpu/graphite/ResourceProvider.h` | 资源提供者 |
| `src/gpu/graphite/AtlasProvider.h` | 图集管理 |
| `src/gpu/graphite/task/TaskList.h` | 任务列表 |
