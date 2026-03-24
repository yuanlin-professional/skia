# GrVkSecondaryCBDrawContext

> 源文件: `include/private/chromium/GrVkSecondaryCBDrawContext.h`

## 概述

GrVkSecondaryCBDrawContext 是专为 Chromium 设计的 Vulkan 二级命令缓冲区绘制上下文，允许将 Skia 的绘制命令直接录制到外部提供的 Vulkan 二级命令缓冲区中。这是一个私有头文件，仅供 Chromium 内部使用，用于实现跨进程的 Vulkan 渲染。

## 架构位置

本类位于 Skia 的 Vulkan 后端实现中，专为 Chromium 的 GPU 进程架构定制。它与 SkCanvas（画布）、GrRecordingContext（录制上下文）和 GrDeferredDisplayList（DDL）配合工作，是 Chromium Vulkan 渲染路径的关键组件。

## 主要类与结构体

### GrVkSecondaryCBDrawContext

Vulkan 二级命令缓冲区绘制上下文类，继承自 SkRefCnt。

**继承关系**: SkRefCnt → GrVkSecondaryCBDrawContext

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fDevice | sk_sp&lt;skgpu::ganesh::Device&gt; | Ganesh 设备对象 |
| fCachedCanvas | std::unique_ptr&lt;SkCanvas&gt; | 缓存的画布指针 |
| fProps | const SkSurfaceProps | 表面属性（常量） |

## 公共 API 函数

### `Make()`

```cpp
static sk_sp<GrVkSecondaryCBDrawContext> Make(GrRecordingContext*,
                                              const SkImageInfo&,
                                              const GrVkDrawableInfo&,
                                              const SkSurfaceProps* props)
```

- **功能**: 创建 Vulkan 二级命令缓冲区绘制上下文
- **参数**:
  - `GrRecordingContext*`: 录制上下文
  - `SkImageInfo`: 图像信息（尺寸、颜色类型等）
  - `GrVkDrawableInfo`: Vulkan 可绘制对象信息
  - `SkSurfaceProps*`: 表面属性（可选）
- **返回值**: 成功返回智能指针，失败返回 nullptr
- **注意**: 二级命令缓冲区必须已调用 begin，并带有 `VK_COMMAND_BUFFER_USAGE_RENDER_PASS_CONTINUE_BIT` 标志

### `getCanvas()`

```cpp
SkCanvas* getCanvas()
```

- **功能**: 获取用于绘制的画布
- **返回值**: SkCanvas 指针（所有权仍属于上下文）
- **用途**: 在此画布上执行所有绘制操作

### `flush()`

```cpp
void flush()
```

- **功能**: 将所有绘制命令记录到导入的二级 VkCommandBuffer，并提交依赖的离屏绘制到 GPU
- **调用时机**: 完成所有绘制操作后
- **效果**: 填充外部提供的二级命令缓冲区

### `wait()`

```cpp
bool wait(int numSemaphores,
          const GrBackendSemaphore waitSemaphores[],
          bool deleteSemaphoresAfterWait = true)
```

- **功能**: 插入 GPU 信号量，让驱动在执行二级命令缓冲区前等待
- **参数**:
  - `numSemaphores`: 信号量数量
  - `waitSemaphores`: 信号量数组
  - `deleteSemaphoresAfterWait`: 是否在等待后由 Skia 删除信号量
- **返回值**: 成功返回 true，失败则 GPU 不会等待任何信号量
- **等待阶段**: VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT 和 VK_PIPELINE_STAGE_TRANSFER_BIT
- **注意**: 信号量提交到 GrContext 拥有的 VkCommandBuffer，而非二级命令缓冲区

### `releaseResources()`

```cpp
void releaseResources()
```

- **功能**: 释放所有持有的资源，包括 Vulkan 对象
- **调用时机**: 在提交二级命令缓冲区并等待 GPU 完成后，删除上下文前
- **警告**: 过早调用会导致 Vulkan 对象在 GPU 使用时被删除

### `props()`

```cpp
const SkSurfaceProps& props() const
```

- **功能**: 获取表面属性
- **返回值**: 表面属性的常量引用

### `characterize()`

```cpp
bool characterize(GrSurfaceCharacterization* characterization) const
```

- **功能**: 生成表面特性描述（DDL 支持）
- **参数**: 输出的特性描述指针
- **返回值**: 成功返回 true

### `draw()`

```cpp
#ifndef SK_DDL_IS_UNIQUE_POINTER
bool draw(sk_sp<const GrDeferredDisplayList> deferredDisplayList)
#else
bool draw(const GrDeferredDisplayList* deferredDisplayList)
#endif
```

- **功能**: 绘制延迟显示列表（DDL 支持）
- **参数**: DDL 智能指针或裸指针（取决于编译配置）
- **返回值**: 成功返回 true

### `isCompatible()`

```cpp
bool isCompatible(const GrSurfaceCharacterization& characterization) const
```

- **功能**: 检查上下文是否与给定的表面特性兼容
- **参数**: 表面特性描述
- **返回值**: 兼容返回 true

## 内部实现细节

### 渲染通道限制

由于二级命令缓冲区必须在 `VK_COMMAND_BUFFER_USAGE_RENDER_PASS_CONTINUE_BIT` 模式下使用，它不能更改渲染通道，导致以下限制：

**不支持的操作**:
- 需要目标拷贝（dst copy）的混合操作会被丢弃
- 文本绘制会被丢弃（可能需要中间文本数据上传）
- 读写像素操作不可用
- 任何需要拷贝的绘制都会失败（包括使用 backdrop filter 的 save layer）
- 模板测试被禁用

**绕过方法**:
客户端可以将不支持的绘制操作先绘制到离屏 SkSurface，然后将结果作为 SkImage 绘制到 GrVkSecondaryCBDrawContext。

### 生命周期管理

1. **创建**: 通过 `Make()` 工厂方法创建
2. **绘制**: 通过 `getCanvas()` 获取画布并执行绘制
3. **刷新**: 调用 `flush()` 将命令录制到二级缓冲区
4. **提交**: 客户端将二级命令缓冲区提交到主命令缓冲区
5. **等待**: 等待 GPU 完成执行
6. **释放**: 调用 `releaseResources()` 清理资源
7. **销毁**: 删除上下文对象

### 信号量机制

`wait()` 方法的工作流程：

1. 客户端传入需要等待的信号量数组
2. Skia 将信号量提交到 GrContext 拥有的 VkCommandBuffer
3. 该命令缓冲区在执行前等待信号量
4. 等待发生在片段着色器和传输阶段之前
5. 如果 `deleteSemaphoresAfterWait` 为 true，Skia 负责删除信号量
6. 否则，客户端需要使用 finishedProcs 确保信号量不会过早删除

### DDL 支持

虽然头文件中有 DDL 相关方法（`characterize()`, `draw()`, `isCompatible()`），但注释表明这些功能尚未完全实现（TODO: Fill out these calls to support DDL）。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| SkRefCnt | 引用计数基类 |
| SkSurfaceProps | 表面属性 |
| GrBackendSemaphore | 后端信号量抽象 |
| GrDeferredDisplayList | 延迟显示列表 |
| GrRecordingContext | 录制上下文 |
| GrSurfaceCharacterization | 表面特性描述 |
| GrVkDrawableInfo | Vulkan 可绘制对象信息 |
| skgpu::ganesh::Device | Ganesh 设备 |
| SkCanvas | 画布接口 |
| SkImageInfo | 图像信息 |

### 被依赖的模块

- Chromium GPU 进程的 Vulkan 渲染路径
- Chromium 的跨进程命令缓冲区共享机制

## 设计模式与设计决策

### 工厂模式

使用静态 `Make()` 方法创建对象，隐藏构造细节，允许在失败时返回 nullptr。

### RAII 资源管理

通过智能指针管理 `fDevice` 和 `fCachedCanvas`，但需要显式调用 `releaseResources()`，这是一种混合策略：
- 自动管理大部分资源
- 关键的 Vulkan 资源需要手动释放（因为需要等待 GPU）

### 私有构造函数

构造函数声明为私有，强制使用工厂方法，确保对象总是正确初始化。

### 惰性画布创建

`fCachedCanvas` 可能在首次调用 `getCanvas()` 时创建，避免了不必要的分配。

## 性能考量

### 零拷贝命令录制

直接录制到外部提供的 Vulkan 命令缓冲区，避免了中间缓冲区的拷贝。

### 离屏渲染优化

对于不支持的操作，建议使用离屏 Surface，虽然增加了拷贝，但保持了功能完整性。

### 信号量同步

通过 `wait()` 方法支持细粒度的 GPU 同步，避免了不必要的 CPU 等待。

### 渲染通道连续性

保持在同一渲染通道内，减少了渲染状态切换开销，但牺牲了灵活性。

## 平台相关说明

### 仅限 Vulkan

该类仅适用于 Vulkan 后端，其他后端（OpenGL、Metal）没有对应的实现。

### Chromium 专用

标注为 `SK_SPI`（Skia Private Interface），仅供 Chromium 使用，不属于 Skia 的公共 API。

### 二级命令缓冲区

依赖 Vulkan 的二级命令缓冲区特性，该特性允许在主命令缓冲区中嵌入子命令缓冲区。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/private/chromium/GrSurfaceCharacterization.h` | 表面特性描述 |
| `include/private/chromium/GrDeferredDisplayList.h` | DDL 支持 |
| `include/core/SkCanvas.h` | 画布接口 |
| `include/gpu/GrBackendSemaphore.h` | 信号量抽象 |
| `include/gpu/ganesh/GrRecordingContext.h` | 录制上下文 |
| `src/gpu/ganesh/Device.h` | Ganesh 设备实现 |
| `include/gpu/vk/GrVkTypes.h` | Vulkan 类型定义 |
