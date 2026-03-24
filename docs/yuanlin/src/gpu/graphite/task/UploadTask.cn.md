# UploadTask

> 源文件
> - src/gpu/graphite/task/UploadTask.h
> - src/gpu/graphite/task/UploadTask.cpp

## 概述

`UploadTask` 是 Skia Graphite 中负责将像素数据从 CPU 内存上传到 GPU 纹理的任务类型。它管理一系列上传操作实例（`UploadInstance`），每个实例封装从上传缓冲区到纹理的拷贝命令。该系统支持多种上传场景：普通纹理上传、压缩纹理上传、mipmap 层级上传、条件化上传（如图像去重）以及主机直接上传（零拷贝优化）。

核心组件包括：`MipLevel` 定义源数据、`UploadSource` 预处理和验证上传参数、`UploadInstance` 封装单次上传操作、`UploadList` 累积待上传数据、`ConditionalUploadContext` 支持动态决策和去重、`UploadTask` 作为任务图节点执行所有上传。系统通过 `UploadBufferManager` 管理上传缓冲区，支持像素格式转换、行字节对齐、压缩数据处理等复杂逻辑。

## 架构位置

`UploadTask` 在纹理数据流转管线中扮演关键角色：

- **数据源头**: 接收来自 `SkImage`、`SkSurface`、`writePixels()` 等 API 的像素数据
- **缓冲区管理**: 通过 `UploadBufferManager` 分配上传缓冲区，写入转换后的数据
- **任务图集成**: 作为 `Task` 节点插入任务图，在渲染前执行上传
- **纹理实例化**: 协助 `TextureProxy` 的延迟实例化，按需分配 GPU 内存
- **重放支持**: 支持录制重放（`Recording::replay()`），包括裁剪和平移

它连接高层 API 的像素操作和底层 GPU 命令，是数据上行路径的核心组件。

## 主要类与结构体

### MipLevel 结构

```cpp
struct MipLevel {
    const void* fPixels = nullptr;  // 像素数据指针
    size_t fRowBytes = 0;            // 每行字节数（0 表示紧密打包）
};
```
描述单个 mipmap 层级的源数据。

### ConditionalUploadContext 抽象类

提供条件化上传机制的基类：

```cpp
virtual bool needsUpload(Context*) = 0
```
决定是否执行上传（动态决策）。

```cpp
virtual bool uploadSubmitted()
```
决定上传后是否保留任务（返回 false 则丢弃，用于一次性上传）。

**ImageUploadContext 实现**: 总是上传但立即丢弃，实现图像去重。

### UploadSource 类

预处理和验证上传源数据：

**成员变量**:
- `STArray<16, MipLevel> fLevels`: mipmap 层级数组
- `bool fCanUploadOnHost`: 是否支持主机直接上传
- `bool fIsRGB888Format`: 是否为 RGB888 格式（需特殊处理）
- `SkTextureCompressionType fCompression`: 压缩类型
- `size_t fBytesPerPixel`: 每像素或压缩块字节数

**静态工厂**:
- `Make()`: 创建普通纹理上传源
- `MakeCompressed()`: 创建压缩纹理上传源

### UploadInstance 类

封装单次上传操作的完整信息：

**成员变量**:
- `const Buffer* fBuffer`: 上传缓冲区指针
- `size_t fBytesPerPixel`: 每像素字节数
- `sk_sp<TextureProxy> fTextureProxy`: 目标纹理代理
- `STArray<1, BufferTextureCopyData> fCopyData`: 拷贝命令数据（支持多个 mipmap 层级）
- `std::unique_ptr<ConditionalUploadContext> fConditionalContext`: 条件化上传上下文

**核心方法**:
- `Make()`: 创建普通纹理上传实例，分配缓冲区并写入转换后数据
- `MakeCompressed()`: 创建压缩纹理上传实例
- `prepareResources()`: 实例化纹理代理
- `addCommand()`: 录制上传命令

### UploadList 类

可变的上传实例容器：

```cpp
bool recordUpload(Recorder*, sk_sp<TextureProxy>, ...)
```
记录一次上传操作，尝试主机直接上传或创建上传实例。

### UploadTask 类

不可变的上传任务：

**成员变量**:
```cpp
STArray<1, UploadInstance> fInstances
```

**静态工厂**:
- `Make(UploadList*)`: 从上传列表创建任务
- `Make(UploadInstance)`: 从单个实例创建任务

**任务接口**:
- `prepareResources()`: 实例化所有纹理代理
- `addCommands()`: 录制所有上传命令
- `visitProxies()`: 遍历写入的纹理代理（非只读）

## 公共 API 函数

### UploadSource 工厂方法

```cpp
static UploadSource Make(const Caps* caps,
                         const TextureProxy& textureProxy,
                         const SkColorInfo& srcColorInfo,
                         const SkColorInfo& dstColorInfo,
                         SkSpan<const MipLevel> levels,
                         const SkIRect& dstRect)
```
创建普通纹理上传源，执行以下验证和预处理：
1. 验证纹理可用性和格式兼容性
2. 验证 mipmap 层级数量（1 或完整层级）
3. 检查所有层级有有效像素数据
4. 查询支持的传输颜色类型
5. 计算每像素字节数（处理 RGB888 特殊情况）
6. 检测是否支持主机直接上传

返回有效的 `UploadSource` 或无效对象（验证失败）。

```cpp
static UploadSource MakeCompressed(const Caps* caps,
                                   const TextureProxy& textureProxy,
                                   const void* data,
                                   size_t dataSize)
```
创建压缩纹理上传源，自动计算 mipmap 偏移并验证数据大小。

### UploadInstance 工厂方法

```cpp
static UploadInstance Make(Recorder* recorder,
                           sk_sp<TextureProxy> textureProxy,
                           const SkColorInfo& srcColorInfo,
                           const SkColorInfo& dstColorInfo,
                           const UploadSource& source,
                           const SkIRect& dstRect,
                           std::unique_ptr<ConditionalUploadContext> condContext)
```
创建上传实例，核心流程：
1. 计算所有 mipmap 层级的缓冲区偏移和对齐行字节
2. 从 `UploadBufferManager` 分配上传缓冲区
3. 遍历每个 mipmap 层级：
   - 执行像素格式转换（如需）
   - 处理 RGB888 格式（从 RGBA 中提取 RGB）
   - 写入对齐后的数据到缓冲区
   - 构建 `BufferTextureCopyData` 拷贝命令参数
4. 记录 Android 跟踪事件

返回有效实例或 `Invalid()` （分配失败）。

```cpp
static UploadInstance MakeCompressed(Recorder*, sk_sp<TextureProxy>, const UploadSource&)
```
创建压缩纹理上传实例，处理压缩块对齐要求。

```cpp
bool prepareResources(ResourceProvider* resourceProvider)
```
实例化纹理代理，支持客户端纹理、临时设备、图集代理等场景。

```cpp
Task::Status addCommand(Context* context,
                       CommandBuffer* commandBuffer,
                       Task::ReplayTargetData replayData) const
```
录制上传命令，处理两种场景：
1. **普通上传**: 调用 `copyBufferToTexture()` 上传所有 mipmap 层级
2. **重放目标上传**: 应用平移、裁剪，调整缓冲区偏移和矩形参数

返回 `kSuccess`、`kFail` 或 `kDiscard`（条件化上传决定丢弃）。

### UploadList 方法

```cpp
bool recordUpload(Recorder* recorder,
                 sk_sp<TextureProxy> textureProxy,
                 const SkColorInfo& srcColorInfo,
                 const SkColorInfo& dstColorInfo,
                 const UploadSource& source,
                 const SkIRect& dstRect,
                 std::unique_ptr<ConditionalUploadContext> condContext)
```
记录上传操作：
- 优先尝试主机直接上传（零拷贝路径）
- 否则创建上传实例并添加到列表

### UploadTask 工厂方法

```cpp
static sk_sp<UploadTask> Make(UploadList* uploadList)
```
从上传列表创建任务，空列表返回 nullptr。

```cpp
static sk_sp<UploadTask> Make(UploadInstance instance)
```
从单个实例创建任务，无效实例返回 nullptr。

### UploadTask 任务接口

```cpp
Status prepareResources(ResourceProvider* resourceProvider, ...)
```
遍历所有实例，调用其 `prepareResources()`，任一失败则整体失败。

```cpp
Status addCommands(Context* context, CommandBuffer* commandBuffer, ReplayTargetData replayData)
```
遍历所有实例，录制上传命令：
- 跳过无效实例（已丢弃）
- 处理 `kDiscard` 状态，标记实例为无效
- 所有实例丢弃则返回 `kDiscard`
- 任一失败则返回 `kFail`

```cpp
bool visitProxies(const std::function<bool(const TextureProxy*)>& visitor, bool readsOnly)
```
遍历写入的纹理代理，`readsOnly=false` 时才执行（上传不读取纹理）。

## 内部实现细节

### compute_combined_buffer_size 函数

计算所有 mipmap 层级的总缓冲区大小和对齐偏移：
- 逐层计算尺寸（每层为上层的一半，最小 1）
- 对每行字节数应用平台对齐要求
- 对每层总大小应用传输缓冲区对齐
- 累积偏移，确保每层起始对齐

返回 `{combinedBufferSize, minAlignment}`。

### 像素格式转换

`UploadInstance::Make()` 中的转换逻辑：
1. 查询后端支持的传输颜色类型（可能与目标格式不同）
2. 构建输入和输出 `SkColorInfo`，处理未知 alpha 类型
3. 比较 `inputColorInfo != supportedColorInfo` 决定是否需转换
4. 转换时使用 `SkConvertPixels()` 或 `writer.convertAndWrite()`

### RGB888 特殊处理

RGB888 格式通常模拟为 RGBA8888：
- 检测 `isRGB888Format` 标志
- 使用 `writer.writeRGBFromRGBx()` 从 RGBA 中提取 RGB
- 可能先转换为支持的 RGBA 格式，再提取 RGB

### 压缩纹理处理

`MakeCompressed()` 方法：
- 使用 `SkCompressedDataSize()` 计算 mipmap 偏移
- 计算压缩块尺寸（`CompressedDimensionsInBlocks`）
- 处理完整上传时的块对齐要求（某些后端需要）
- 紧密打包源数据（`fRowBytes = 0`）

### 条件化上传机制

通过 `ConditionalUploadContext` 实现：
1. 在 `addCommand()` 中调用 `needsUpload()` 决定是否执行
2. 执行后调用 `uploadSubmitted()` 决定是否保留任务
3. `ImageUploadContext` 实现一次性上传：`needsUpload()` 返回 true，`uploadSubmitted()` 返回 false

用于图像纹理去重：首次遇到上传，后续重放跳过。

### 重放目标处理

`addCommand()` 中的重放逻辑：
- 检测目标纹理是否为重放目标（`replayData.fTarget`）
- 应用平移（`dstRect.offset(replayData.fTranslation)`）
- 应用裁剪（与 `replayData.fClip` 求交）
- 调整缓冲区偏移：`fBufferOffset += (croppedY - origY) * rowBytes + (croppedX - origX) * bpp`
- 仅处理单层级（断言 `fCopyData.size() == 1`）

### 主机直接上传优化

`UploadList::recordUpload()` 中：
```cpp
if (source.canUploadOnHost()) {
    return textureProxy->texture()->uploadDataOnHost(source, dstRect);
}
```
- 零拷贝路径，直接写入映射的纹理内存
- 需要后端支持（如 Metal 的共享存储模式）
- 跳过上传缓冲区和命令录制

### 错误处理

- **缓冲区分配失败**: 记录警告日志，返回 `Invalid()`
- **纹理实例化失败**: 记录错误日志，返回 false
- **命令录制失败**: 返回 `kFail`，传播到任务图

### 跟踪支持

使用 `ATRACE_ANDROID_FRAMEWORK` 宏记录上传事件：
```cpp
ATRACE_ANDROID_FRAMEWORK("Upload %sTexture [%dx%d]",
                         mipLevelCount > 1 ? "MipMap " : "",
                         dstRect.width(), dstRect.height());
```
在 Android 平台上生成系统跟踪事件，用于性能分析。

## 依赖关系

### 直接依赖

**核心类型**:
- `src/gpu/graphite/task/Task.h`: 任务基类
- `src/gpu/graphite/TextureProxy.h`: 纹理代理
- `src/gpu/graphite/Buffer.h`: 缓冲区对象
- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区

**资源管理**:
- `src/gpu/graphite/UploadBufferManager.h`: 上传缓冲区管理
- `src/gpu/graphite/ResourceProvider.h`: 资源提供者
- `src/gpu/graphite/Caps.h`: 能力查询

**像素处理**:
- `src/core/SkConvertPixels.h`: 像素格式转换
- `src/core/SkCompressedDataUtils.h`: 压缩数据工具
- `src/core/SkMipmap.h`: Mipmap 层级计算
- `src/gpu/DataUtils.h`: GPU 数据工具

### 被使用场景

- **SkImage 上传**: 图像纹理的首次上传
- **writePixels**: 客户端写入像素到纹理
- **图集管理**: 字形图集、光栅图集的上传
- **临时设备**: 离屏表面的纹理上传

### 协作对象

- **Recorder**: 录制上下文，提供 `UploadBufferManager` 和 `Caps`
- **UploadBufferManager**: 管理上传缓冲区池，分配映射内存
- **TextureProxy**: 延迟纹理实例化，获取目标纹理
- **CommandBuffer**: 录制 `copyBufferToTexture` 命令
- **Texture**: 主机直接上传的目标对象

## 设计模式与设计决策

### 分阶段处理

三个阶段分离：
1. **UploadSource**: 验证和预处理源数据
2. **UploadInstance**: 分配缓冲区并写入数据
3. **UploadTask**: 执行命令录制

优点：错误早检测、资源分配延迟、命令录制高效。

### 条件化上传模式

通过虚接口 `ConditionalUploadContext` 支持动态决策：
- 策略模式：不同上传场景实现不同策略
- 去重优化：`ImageUploadContext` 实现一次性上传
- 扩展性：客户端可实现自定义条件（如时间戳、版本号）

### 主机直接上传快速路径

优先尝试零拷贝上传：
- 性能优化：避免缓冲区中转和命令开销
- 平台特性：利用统一内存架构（UMA）
- 透明回退：不支持时自动使用缓冲区路径

### Mipmap 批量处理

单个实例处理所有 mipmap 层级：
- 减少实例数量：一个纹理一个实例
- 批量命令：一次 `copyBufferToTexture` 调用
- 缓冲区紧凑：连续分配所有层级内存

### 延迟实例化支持

`prepareResources()` 阶段实例化纹理：
- 支持 `TextureProxy` 的延迟分配机制
- 允许任务图优化（去重、合并）
- 适应图集代理等特殊场景

### RGB888 模拟处理

专门处理 RGB888 到 RGBA 的模拟：
- 后端兼容性：大多数 GPU 不原生支持 RGB888
- 数据提取：从 RGBA 中跳过 alpha 通道
- 节省带宽：上传 RGB 而非 RGBA

## 性能考量

### 缓冲区池化

通过 `UploadBufferManager` 复用缓冲区：
- 减少分配开销：重用已分配的大缓冲区
- 减少碎片：统一管理避免小块分配
- 批量提交：累积多个上传到同一缓冲区

### 对齐优化

严格对齐要求提升 GPU 效率：
- **行字节对齐**: `getAlignedTextureDataRowBytes()` 满足 GPU 缓存行
- **缓冲区对齐**: `requiredTransferBufferAlignment()` 满足 DMA 要求
- **块对齐**: 压缩纹理满足块边界要求

### 格式转换策略

最小化转换开销：
- 仅在必要时转换（`inputColorInfo != supportedColorInfo`）
- 使用优化的 `SkConvertPixels()`（SIMD 加速）
- RGB888 使用专用快速路径

### 主机直接上传

零拷贝路径显著减少开销：
- 无中间缓冲区分配
- 无数据拷贝
- 无命令录制和提交
- 适用于统一内存架构（Metal、某些 Vulkan 实现）

### 批量上传

单个任务处理多个实例：
- 减少任务对象数量
- 批量实例化纹理
- 连续录制命令

### 条件化上传

去重机制节省带宽：
- 图像纹理仅首次上传
- 后续重放跳过上传命令
- 减少 GPU 工作量和内存带宽

### 重放优化

裁剪和平移避免无效上传：
- 跳过完全在裁剪区外的上传
- 仅上传可见部分
- 调整缓冲区偏移减少数据传输

## 相关文件

### 任务系统

- `src/gpu/graphite/task/Task.h`: 任务基类
- `src/gpu/graphite/task/DrawTask.h`: 绘制任务（可包含上传前置）
- `src/gpu/graphite/task/TaskList.h`: 任务列表容器
- `src/gpu/graphite/task/CopyTask.h`: 纹理拷贝任务

### 缓冲区与纹理

- `src/gpu/graphite/Buffer.h`: GPU 缓冲区对象
- `src/gpu/graphite/Texture.h`: GPU 纹理对象
- `src/gpu/graphite/TextureProxy.h`: 纹理代理
- `src/gpu/graphite/UploadBufferManager.h`: 上传缓冲区管理器

### 命令系统

- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区
- `src/gpu/graphite/CommandTypes.h`: 命令类型定义（`BufferTextureCopyData`）

### 资源管理

- `src/gpu/graphite/ResourceProvider.h`: 资源提供者
- `src/gpu/graphite/Caps.h`: 能力查询接口
- `src/gpu/graphite/TextureInfo.h`: 纹理信息

### 像素处理

- `src/core/SkConvertPixels.h`: 像素格式转换
- `src/core/SkCompressedDataUtils.h`: 压缩纹理工具
- `src/core/SkMipmap.h`: Mipmap 计算
- `src/gpu/DataUtils.h`: GPU 数据工具

### 上层接口

- `include/gpu/graphite/Recorder.h`: 录制器接口
- `include/gpu/graphite/Recording.h`: 录制对象
- `include/core/SkImage.h`: 图像接口（触发上传）
- `include/core/SkSurface.h`: 表面接口（`writePixels`）
