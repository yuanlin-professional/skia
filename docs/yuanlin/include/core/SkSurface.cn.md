# SkSurface

> 源文件: `include/core/SkSurface.h`

## 概述

`SkSurface` 是 Skia 图形库中最核心的类之一，负责管理画布（Canvas）所绘制的目标像素存储。它是连接绘图操作与实际像素数据之间的桥梁。像素可以分配在 CPU 内存中（光栅表面）或 GPU 上（GrRenderTarget 表面）。

该文件同时定义了 `SkSurfaces` 命名空间，其中包含了创建各类 Surface 的工厂函数。客户端通过工厂函数创建 `SkSurface` 实例，然后通过 `getCanvas()` 获取画布进行绘制，最后可通过 `makeImageSnapshot()` 等方法获取绘制结果。

`SkSurface` 继承自 `SkRefCnt`，采用引用计数管理生命周期。Skia 明确建议客户端不应子类化 `SkSurface`，因为大量内部机制是非公开的。

## 架构位置

`SkSurface` 在 Skia 架构中处于核心绘制管线的顶层：

```
SkSurface（绘制目标管理）
├── SkCanvas（绘制命令发送）
│   ├── SkPaint（绘制样式）
│   ├── SkPath（路径几何）
│   └── ...
├── SkImage（图像快照输出）
├── SkPixmap / SkBitmap（像素数据访问）
└── GPU 后端
    ├── GrRecordingContext (Ganesh)
    └── skgpu::graphite::Recorder (Graphite)
```

`SkSurface` 是客户端进行 Skia 绘制的主要入口点。所有的绘制操作都需要一个 Surface 作为目标。

## 主要类与结构体

### `SkSurfaces` 命名空间

包含 Surface 创建相关的工厂函数和辅助类型。

#### `SkSurfaces::BackendSurfaceAccess` 枚举
```cpp
enum class BackendSurfaceAccess {
    kNoAccess,  // 后端表面不会被客户端使用
    kPresent,   // 后端表面将用于显示到屏幕
};
```
用于指示客户端对后端表面的访问意图，帮助 Skia 优化同步和资源管理策略。

#### `SkSurfaces::PixelsReleaseProc` 类型别名
```cpp
using PixelsReleaseProc = void(void* pixels, void* context);
```
用于在 Surface 销毁时释放客户端提供的像素内存的回调函数类型。

### `SkSurface` 类

继承自 `SkRefCnt` 的主要表面类，提供绘制目标管理的完整功能。

#### `ContentChangeMode` 枚举
```cpp
enum ContentChangeMode {
    kDiscard_ContentChangeMode,  // 内容变更时丢弃表面数据
    kRetain_ContentChangeMode,   // 内容变更时保留表面数据
};
```

#### `BackendHandleAccess` 枚举
```cpp
enum class BackendHandleAccess {
    kFlushRead,      // 后端对象可读
    kFlushWrite,     // 后端对象可写
    kDiscardWrite,   // 后端对象必须被覆写
};
```
控制访问后端 GPU 对象时的刷新行为。

#### 类型别名
```cpp
using ReleaseContext = void*;
using TextureReleaseProc = void (*)(ReleaseContext);
using AsyncReadResult = SkImage::AsyncReadResult;
using ReadPixelsContext = void*;
using ReadPixelsCallback = void(ReadPixelsContext, std::unique_ptr<const AsyncReadResult>);
using RescaleGamma = SkImage::RescaleGamma;
using RescaleMode = SkImage::RescaleMode;
```

## 公共 API 函数

### 工厂函数（`SkSurfaces` 命名空间）

#### `SkSurfaces::Null`
```cpp
SK_API sk_sp<SkSurface> Null(int width, int height);
```
创建一个无后备像素的空 Surface。对返回的 Canvas 进行绘制没有实际效果，调用 `makeImageSnapshot()` 返回 `nullptr`。主要用于测试和度量目的。

#### `SkSurfaces::Raster`
```cpp
SK_API sk_sp<SkSurface> Raster(const SkImageInfo& imageInfo, size_t rowBytes,
                                const SkSurfaceProps* surfaceProps);
inline sk_sp<SkSurface> Raster(const SkImageInfo& imageInfo,
                                const SkSurfaceProps* props = nullptr);
```
创建光栅（CPU）Surface，自动分配像素内存。Canvas 直接绘制到分配的像素中。像素内存在创建时被清零，并在 Surface 销毁时释放。要求 `imageInfo` 的尺寸大于零，且颜色类型和 Alpha 类型需被光栅表面支持。

#### `SkSurfaces::WrapPixels`
```cpp
SK_API sk_sp<SkSurface> WrapPixels(const SkImageInfo& imageInfo, void* pixels,
                                    size_t rowBytes, const SkSurfaceProps* surfaceProps = nullptr);
inline sk_sp<SkSurface> WrapPixels(const SkPixmap& pm,
                                    const SkSurfaceProps* props = nullptr);
SK_API sk_sp<SkSurface> WrapPixels(const SkImageInfo& imageInfo, void* pixels,
                                    size_t rowBytes, PixelsReleaseProc, void* context,
                                    const SkSurfaceProps* surfaceProps = nullptr);
```
在客户端提供的像素缓冲区上创建 Surface。像素不会被初始化。带 `releaseProc` 的版本会在 Surface 销毁时调用回调来释放像素。这允许客户端完全控制像素内存的分配和释放。

### `SkSurface` 实例方法

#### 属性查询

```cpp
int width() const;
int height() const;
virtual SkImageInfo imageInfo() const;
uint32_t generationID();
const SkSurfaceProps& props() const;
```
- `width()` / `height()` 返回表面的像素尺寸。
- `imageInfo()` 返回描述表面的 `SkImageInfo`（颜色类型、Alpha 类型、色彩空间等）。
- `generationID()` 返回唯一标识当前内容的 ID，每次内容变化时都会改变。
- `props()` 返回表面属性（LCD 条纹方向、设备无关字体设置等）。

#### 兼容性检查

```cpp
bool isCompatible(const GrSurfaceCharacterization& characterization) const;
```
检查当前 Surface 是否与给定的特性描述兼容，主要用于判断是否可以应用 `GrDeferredDisplayList`。

#### 画布和能力

```cpp
SkCanvas* getCanvas();
sk_sp<const SkCapabilities> capabilities();
```
- `getCanvas()` 返回 Surface 拥有的 Canvas 对象（不要手动删除该对象）。后续调用返回同一 Canvas 实例。
- `capabilities()` 返回描述设备能力的 `SkCapabilities` 对象。

#### 上下文访问

```cpp
GrRecordingContext* recordingContext() const;
skgpu::graphite::Recorder* recorder() const;
SkRecorder* baseRecorder() const;
```
分别获取 Ganesh 录制上下文、Graphite 录制器和基础录制器。

#### 创建兼容 Surface

```cpp
sk_sp<SkSurface> makeSurface(const SkImageInfo& imageInfo);
sk_sp<SkSurface> makeSurface(int width, int height);
```
创建与当前 Surface 具有相同属性（光栅/GPU/空）但不共享像素的新 Surface。

#### 图像快照

```cpp
sk_sp<SkImage> makeImageSnapshot();
sk_sp<SkImage> makeImageSnapshot(const SkIRect& bounds);
sk_sp<SkImage> makeTemporaryImage();
```
- `makeImageSnapshot()` 捕获当前 Surface 内容为 SkImage。后续对 Surface 的绘制不会影响已创建的 Image。
- 带 bounds 参数的版本只捕获指定子矩形。
- `makeTemporaryImage()` 创建临时图像，性能更优但内容有效性依赖于 Surface 不被再次写入。适用于立即销毁 Surface 或确保在再次写入前销毁 Image 的场景。

#### 绘制到其他 Canvas

```cpp
void draw(SkCanvas* canvas, SkScalar x, SkScalar y,
          const SkSamplingOptions& sampling, const SkPaint* paint);
void draw(SkCanvas* canvas, SkScalar x, SkScalar y, const SkPaint* paint = nullptr);
```
将 Surface 内容绘制到另一个 Canvas 上。可选地应用颜色过滤、Alpha、图像过滤和混合模式。

#### 像素读取

```cpp
bool peekPixels(SkPixmap* pixmap);
bool readPixels(const SkPixmap& dst, int srcX, int srcY);
bool readPixels(const SkImageInfo& dstInfo, void* dstPixels, size_t dstRowBytes,
                int srcX, int srcY);
bool readPixels(const SkBitmap& dst, int srcX, int srcY);
```
- `peekPixels()` 直接获取像素数据的指针（仅对光栅 Surface 有效）。
- `readPixels()` 提供三种重载，支持从 Surface 复制像素到 `SkPixmap`、裸指针缓冲区或 `SkBitmap`。支持颜色类型和 Alpha 类型的自动转换。负的 srcX/srcY 值可用于偏移复制区域。

注意：Graphite 后端已废弃同步 readPixels，推荐使用 `skgpu::graphite::Context` 上的异步 API。

#### 异步像素读取

```cpp
void asyncRescaleAndReadPixels(const SkImageInfo& info, const SkIRect& srcRect,
                                RescaleGamma rescaleGamma, RescaleMode rescaleMode,
                                ReadPixelsCallback callback, ReadPixelsContext context);
void asyncRescaleAndReadPixelsYUV420(...);
void asyncRescaleAndReadPixelsYUVA420(...);
```
异步读取像素并可选地进行缩放和色彩空间转换。支持 RGB 和 YUV420/YUVA420 输出格式。当前异步读取仅在 Ganesh GPU 后端中且底层 3D API 支持传输缓冲区和 CPU/GPU 同步时可用。

YUV420 版本将数据输出为三个平面（Y/U/V），U 和 V 平面为半尺寸。YUVA420 增加了全分辨率的 Alpha 平面。

#### 像素写入

```cpp
void writePixels(const SkPixmap& src, int dstX, int dstY);
void writePixels(const SkBitmap& src, int dstX, int dstY);
```
将像素数据从 `SkPixmap` 或 `SkBitmap` 写入 Surface。

#### 后端纹理操作

```cpp
virtual bool replaceBackendTexture(const GrBackendTexture& backendTexture,
                                    GrSurfaceOrigin origin,
                                    ContentChangeMode mode = kRetain_ContentChangeMode,
                                    TextureReleaseProc = nullptr,
                                    ReleaseContext = nullptr) = 0;
```
替换通过 `MakeFromBackendTexture` 创建的 Surface 的后端纹理。旧纹理的内容会被复制到新纹理中。新纹理的格式和尺寸必须与原纹理匹配。

#### GPU 同步

```cpp
bool wait(int numSemaphores, const GrBackendSemaphore* waitSemaphores,
          bool deleteSemaphoresAfterWait = true);
```
插入 GPU 信号量等待，确保在继续在此 Surface 上执行 GPU 命令之前，等待指定的信号量被通知。主要用于跨 GPU 队列或上下文间的同步。

#### Surface 特性描述

```cpp
bool characterize(GrSurfaceCharacterization* characterization) const;
```
获取 Surface 的特性描述（`GrSurfaceCharacterization`），可用于在独立线程中进行 GPU 后端处理。这是延迟渲染列表（`GrDeferredDisplayList`）功能的基础，用于实现分块并行录制。光栅 Surface 返回 false。

#### 内容变更通知

```cpp
void notifyContentWillChange(ContentChangeMode mode);
```
通知 Skia 表面内容将在 Skia 外部被修改。调用后 `generationID()` 将返回不同的值。

## 内部实现细节

### 受保护的构造函数

```cpp
SkSurface(int width, int height, const SkSurfaceProps* surfaceProps);
SkSurface(const SkImageInfo& imageInfo, const SkSurfaceProps* surfaceProps);
```
构造函数是受保护的，强制客户端通过工厂函数创建实例。

### 代数标识符管理

```cpp
void dirtyGenerationID() { fGenerationID = 0; }
```
子类在内容改变时调用此方法，将 `fGenerationID` 重置为 0，使得下次调用 `generationID()` 时生成新的唯一 ID。

### 私有成员

```cpp
const SkSurfaceProps fProps;     // 表面属性
const int            fWidth;     // 宽度（不可变）
const int            fHeight;    // 高度（不可变）
uint32_t             fGenerationID;  // 内容代数标识符
```
宽度、高度和表面属性在创建后不可修改，体现了 Surface 尺寸不变的设计约束。

## 依赖关系

- **`include/core/SkImage.h`** - 图像类，用于快照输出和异步读取类型定义
- **`include/core/SkImageInfo.h`** - 图像信息描述（颜色类型、Alpha 类型、尺寸等）
- **`include/core/SkPixmap.h`** - 像素映射，用于像素读写操作
- **`include/core/SkRefCnt.h`** - 引用计数基类
- **`include/core/SkSamplingOptions.h`** - 采样选项
- **`include/core/SkScalar.h`** - 标量类型定义
- **`include/core/SkSurfaceProps.h`** - 表面属性
- **`include/core/SkTypes.h`** - 基础类型定义
- **前向声明依赖**: `GrBackendSemaphore`, `GrBackendTexture`, `GrRecordingContext`, `GrSurfaceCharacterization`, `SkBitmap`, `SkCanvas`, `SkCapabilities`, `SkColorSpace`, `SkPaint`, `SkRecorder`, `skgpu::graphite::Recorder` 等

## 设计模式与设计决策

### 1. 工厂方法模式
所有 Surface 创建都通过 `SkSurfaces` 命名空间中的静态工厂函数完成，而非直接构造。这使得 Skia 可以根据参数选择最合适的内部实现子类，客户端无需了解具体实现细节。

### 2. 不可变尺寸
Surface 的宽度和高度在创建后不可改变（`const int`），简化了内部资源管理逻辑。需要不同尺寸时必须创建新的 Surface。

### 3. 延迟拷贝语义（Copy-on-Write）
`makeImageSnapshot()` 通常不会立即复制像素数据，而是在后续 Surface 被修改时才执行拷贝。`makeTemporaryImage()` 更进一步，完全避免了拷贝，但代价是 Image 内容的有效性取决于 Surface 是否被再次写入。

### 4. 命名空间工厂函数
将工厂函数放在 `SkSurfaces` 命名空间而非作为 `SkSurface` 的静态方法，遵循了 Skia 现代 API 的设计趋势，更好地组织了大量创建方法。

### 5. 异步 API 设计
异步像素读取使用回调模式（`ReadPixelsCallback`），允许 GPU 在后台完成数据传输，避免了 CPU/GPU 同步等待，是高性能 GPU 编程的标准模式。

### 6. 多后端抽象
通过 `recordingContext()` 和 `recorder()` 分别支持 Ganesh 和 Graphite 两套 GPU 后端，同时保持统一的 Surface 接口。

## 性能考量

1. **`makeTemporaryImage()` vs `makeImageSnapshot()`**: 前者性能更好因为永远不会执行内部拷贝，但使用条件更严格。在确定使用模式满足条件时应优先使用。

2. **异步像素读取**: `asyncRescaleAndReadPixels` 系列方法通过异步回调避免了 CPU 等待 GPU 完成数据传输的阻塞，显著提升了管线并行度。

3. **`peekPixels()` vs `readPixels()`**: 前者直接返回像素指针（零拷贝），但仅在光栅 Surface 上可用。后者需要数据拷贝但适用范围更广。

4. **Surface 兼容性检查**: `isCompatible()` 和 `characterize()` 支持延迟渲染列表机制，允许在独立线程中预录制绘制命令，实现分块并行渲染。

5. **GPU 信号量**: `wait()` 方法提供了细粒度的 GPU 同步控制，仅保证阻塞传输和片段着色器工作，在某些后端可能阻塞更早的管线阶段。

6. **`generationID()` 机制**: 通过轻量级的代数标识符追踪内容变化，避免了昂贵的内容比较操作，常用于缓存失效检测。

## 相关文件

- `include/core/SkCanvas.h` - 绘图 Canvas 类
- `include/core/SkImage.h` - 图像类，Surface 快照的输出类型
- `include/core/SkImageInfo.h` - 图像格式信息
- `include/core/SkPixmap.h` - 像素映射工具
- `include/core/SkBitmap.h` - 位图类
- `include/core/SkRefCnt.h` - 引用计数基类
- `include/core/SkSurfaceProps.h` - 表面属性定义
- `include/gpu/ganesh/GrDirectContext.h` - Ganesh GPU 上下文
- `include/gpu/ganesh/SkSurfaceGanesh.h` - Ganesh 专用的 Surface 创建函数
- `include/gpu/graphite/Surface.h` - Graphite 专用的 Surface 创建函数
- `src/image/SkSurface_Base.h` - Surface 内部基类实现
