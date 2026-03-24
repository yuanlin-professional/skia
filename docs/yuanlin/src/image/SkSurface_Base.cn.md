# SkSurface_Base

> 源文件：src/image/SkSurface_Base.h, src/image/SkSurface_Base.cpp

## 概述

`SkSurface_Base` 是 Skia 中所有表面（Surface）实现的抽象基类。它扩展了公共 API 类 `SkSurface`，提供了内部实现需要的虚函数接口和通用功能。该类管理 Canvas 缓存、图像快照缓存、写时复制（COW）机制、生成 ID 分配等核心功能，为栅格表面、Ganesh 表面、Graphite 表面等不同后端提供统一的实现框架。

作为抽象基类，`SkSurface_Base` 定义了表面的生命周期管理、像素访问、异步读取、绘制操作等关键接口，子类通过重写虚函数实现特定后端的功能。

## 架构位置

`SkSurface_Base` 在 Skia 架构中的位置：

- **继承关系**：继承自公共 API 类 `SkSurface`
- **派生类**：`SkSurface_Raster`、`SkSurface_Ganesh`、`SkSurface_Graphite`、`SkNullSurface`
- **类型系统**：通过 `Type` 枚举区分不同表面后端
- **所属模块**：`src/image/` 表面和图像模块
- **辅助转换**：`asSB()` 和 `asConstSB()` 函数进行类型转换

## 主要类与结构体

### SkSurface_Base

表面实现的抽象基类。

**Type 枚举**：
```cpp
enum class Type {
    kNull,      // 空表面（不绘制）
    kGanesh,    // Ganesh GPU 后端
    kGraphite,  // Graphite GPU 后端
    kRaster,    // CPU 栅格后端
};
```

**核心虚函数**：
- `onNewCanvas()`：创建 Canvas（纯虚）
- `onNewSurface()`：创建兼容表面（纯虚）
- `onNewImageSnapshot()`：创建快照图像
- `onWritePixels()`：写入像素（纯虚）
- `onCopyOnWrite()`：写时复制处理（纯虚）
- `onDraw()`：绘制表面内容
- `onAsyncRescaleAndReadPixels()`：异步缩放和读取像素

**缓存管理成员**：
- `fCachedCanvas`：缓存的 Canvas 指针
- `fOwnedBaseCanvas`：拥有的基础 Canvas
- `fCachedImage`：缓存的快照图像

### 内联方法

**getCachedCanvas()**：
```cpp
SkCanvas* SkSurface_Base::getCachedCanvas() {
    if (nullptr == fCachedCanvas) {
        fOwnedBaseCanvas = std::unique_ptr<SkCanvas>(this->onNewCanvas());
        if (this->baseRecorder()) {
            fCachedCanvas = this->baseRecorder()->makeCaptureCanvas(fOwnedBaseCanvas.get());
        }
        if (!fCachedCanvas) {
            fCachedCanvas = fOwnedBaseCanvas.get();
        }
        if (fCachedCanvas) {
            fCachedCanvas->setSurfaceBase(this);
        }
    }
    return fCachedCanvas;
}
```

**refCachedImage()**：
```cpp
sk_sp<SkImage> SkSurface_Base::refCachedImage() {
    if (fCachedImage) {
        return fCachedImage;
    }
    this->createCaptureBreakpoint();
    fCachedImage = this->onNewImageSnapshot();
    return fCachedImage;
}
```

## 公共 API 函数

### 虚函数接口

**onNewCanvas()**：纯虚函数，创建绘制 Canvas
**onNewSurface()**：纯虚函数，创建兼容表面
**onNewImageSnapshot()**：创建快照图像，默认返回 `nullptr`
**onWritePixels()**：纯虚函数，写入像素数据
**onCopyOnWrite()**：纯虚函数，处理写时复制

### 默认实现

**onDraw()**：
```cpp
void SkSurface_Base::onDraw(SkCanvas* canvas, SkScalar x, SkScalar y,
                            const SkSamplingOptions& sampling, const SkPaint* paint) {
    auto image = this->makeTemporaryImage();
    if (image) {
        canvas->drawImage(image.get(), x, y, sampling, paint);
    }
}
```

**onAsyncRescaleAndReadPixels()**：
```cpp
void SkSurface_Base::onAsyncRescaleAndReadPixels(...) {
    SkBitmap src;
    SkPixmap peek;
    if (this->peekPixels(&peek)) {
        src.installPixels(peek);
    } else {
        src.allocPixels();
        this->readPixels(src, ...);
    }
    return SkRescaleAndReadPixels(src, info, srcRect, rescaleGamma, rescaleMode, callback, context);
}
```

### 辅助方法

**type()**：返回表面类型，默认 `Type::kNull`
**isRasterBacked()**：检查是否为栅格表面
**isGaneshBacked()**：检查是否为 Ganesh 表面
**isGraphiteBacked()**：检查是否为 Graphite 表面

## 内部实现细节

### Canvas 缓存机制

```cpp
SkCanvas* fCachedCanvas = nullptr;
std::unique_ptr<SkCanvas> fOwnedBaseCanvas = nullptr;
```

**缓存策略**：
- 首次调用 `getCanvas()` 时通过 `onNewCanvas()` 创建
- 如果有捕获管理器，包装为捕获 Canvas
- 缓存 Canvas 指针以便后续快速访问
- 表面销毁时自动清理 Canvas

### 图像快照缓存

```cpp
sk_sp<SkImage> fCachedImage = nullptr;
```

**缓存行为**：
- 首次 `makeImageSnapshot()` 创建并缓存图像
- 后续调用返回缓存的图像
- 表面修改时自动清除缓存（通过 `aboutToDraw()`）

### 写时复制（COW）流程

```cpp
bool SkSurface_Base::aboutToDraw(ContentChangeMode mode) {
    this->dirtyGenerationID();

    if (fCachedImage) {
        bool unique = fCachedImage->unique();
        if (!unique) {
            if (!this->onCopyOnWrite(mode)) {
                return false;  // COW 失败
            }
        }
        fCachedImage.reset();  // 清除缓存

        if (unique) {
            this->onRestoreBackingMutability();
        }
    } else if (kDiscard_ContentChangeMode == mode) {
        this->onDiscard();
    }
    return true;
}
```

**COW 触发条件**：
1. 存在缓存图像
2. 图像被外部持有（`!unique()`）

**COW 后操作**：
- 清除图像缓存
- 如果图像唯一，恢复像素可变性

### 生成 ID 管理

```cpp
uint32_t SkSurface_Base::newGenerationID() {
    static std::atomic<uint32_t> nextID{1};
    return nextID.fetch_add(1, std::memory_order_relaxed);
}
```

使用原子操作生成全局唯一的生成 ID，线程安全。

### 未实现快照检测

```cpp
bool SkSurface_Base::outstandingImageSnapshot() const {
    return fCachedImage && !fCachedImage->unique();
}
```

检测是否有外部持有的快照，用于判断是否需要 COW。

### 异步读取像素

默认实现通过同步读取 + 回调实现：

```cpp
void SkSurface_Base::onAsyncRescaleAndReadPixels(...) {
    SkBitmap src;
    // 尝试零拷贝访问
    if (this->peekPixels(&peek)) {
        src.installPixels(peek);
    } else {
        // 回退到拷贝
        src.allocPixels();
        this->readPixels(src, ...);
    }
    // 调用同步缩放和读取
    SkRescaleAndReadPixels(src, ...);
}
```

子类可重写以提供真正的异步实现（如 GPU 异步）。

### 捕获断点

```cpp
void SkSurface_Base::createCaptureBreakpoint() {
    if (this->baseRecorder()) {
        this->baseRecorder()->createCaptureBreakpoint(this);
    }
}
```

支持将表面绘制记录分割为多个 Picture，用于调试和性能分析。

## 依赖关系

### 核心依赖

| 依赖项 | 用途 |
|--------|------|
| `SkSurface` | 基类，公共 API |
| `SkCanvas` | 绘制接口 |
| `SkImage` | 快照图像 |
| `SkPixmap` | 像素数据访问 |
| `SkRescaleAndReadPixels` | 异步读取像素实现 |

### 子类实现

| 子类 | 后端 | 说明 |
|------|------|------|
| `SkSurface_Raster` | CPU | 栅格表面 |
| `SkSurface_Ganesh` | GPU (Ganesh) | Ganesh 表面 |
| `SkSurface_Graphite` | GPU (Graphite) | Graphite 表面 |
| `SkNullSurface` | None | 空表面（不绘制） |

## 设计模式与设计决策

### 模板方法模式

`SkSurface_Base` 定义算法框架，子类实现具体步骤：
- `getCachedCanvas()` 调用 `onNewCanvas()`
- `refCachedImage()` 调用 `onNewImageSnapshot()`
- `aboutToDraw()` 调用 `onCopyOnWrite()`

### 缓存代理模式

**Canvas 缓存**：避免重复创建开销
**图像缓存**：支持 COW 优化

### 决策 1：双层 Canvas 缓存

```cpp
SkCanvas* fCachedCanvas;              // 实际返回的指针
std::unique_ptr<SkCanvas> fOwnedBaseCanvas;  // 拥有的基础 Canvas
```

- **原因**：支持捕获 Canvas 包装
- **灵活性**：`fCachedCanvas` 可以指向基础或包装 Canvas

### 决策 2：COW 在 `aboutToDraw()` 中处理

- **原因**：集中管理表面修改前的准备工作
- **统一性**：所有修改操作（绘制、写像素）都经过此方法

### 决策 3：生成 ID 延迟分配

```cpp
if (0 == fGenerationID) {
    fGenerationID = asSB(this)->newGenerationID();
}
```

- **原因**：不是所有表面都需要生成 ID
- **优化**：按需分配，节省内存和原子操作

### 决策 4：YUV420 读取默认失败

```cpp
void onAsyncRescaleAndReadPixelsYUV420(...) {
    // TODO: 转换 RGB 到 YUV420
    callback(context, nullptr);  // 默认失败
}
```

- **原因**：RGB 到 YUV 转换复杂且不常用
- **策略**：需要的子类自行实现

### 决策 5：析构时清理 Canvas 回调

```cpp
~SkSurface_Base() {
    if (fCachedCanvas) {
        fCachedCanvas->setSurfaceBase(nullptr);
        fCachedCanvas->onSurfaceDelete();
    }
}
```

- **原因**：防止悬空指针（Canvas 可能比表面存活更久）
- **安全性**：通知 Canvas 表面已销毁

## 性能考量

### Canvas 缓存收益

**无缓存**（每次创建）：
```cpp
// O(1) 但有分配开销
SkCanvas* canvas = surface->getCanvas();
```

**有缓存**：
```cpp
// O(1) 且无开销，直接返回指针
SkCanvas* canvas = surface->getCanvas();
```

### 图像快照缓存

**首次快照**：O(1)（COW）或 O(W×H)（拷贝）
**后续快照**：O(1)（返回缓存）

### COW 开销

**检查成本**：O(1)（引用计数检查）
**拷贝成本**：O(W×H)（触发时）

### 生成 ID 分配

原子操作开销极小（~10ns），可忽略。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkSurface.h` | 基类 | 公共表面 API |
| `src/image/SkSurface_Raster.h` | 派生类 | 栅格表面实现 |
| `include/core/SkCanvas.h` | 核心依赖 | 绘制接口 |
| `include/core/SkImage.h` | 快照类型 | 图像接口 |
| `src/image/SkRescaleAndReadPixels.h` | 工具 | 像素读取实现 |
| `src/capture/SkCaptureCanvas.h` | 捕获 | Canvas 捕获支持 |
