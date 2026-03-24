# SkImage_Base - SkImage 内部基类

> 源文件:
> - `src/image/SkImage_Base.h`
> - `src/image/SkImage_Base.cpp`

## 概述

SkImage_Base 是 Skia 图像系统的内部基类，继承自公共的 `SkImage` 类。它定义了所有具体 SkImage 实现必须遵循的内部接口，包括像素读取、mipmap 管理、异步缩放读取、GPU 上下文访问等功能。该类是 Skia 支持多种图像后端（Raster、Ganesh、Graphite、Lazy 等）的关键抽象层。

## 架构位置

```
Skia 图像系统
├── SkImage (公共 API)
│   └── SkImage_Base (本模块 - 内部基类)
│       ├── SkImage_Raster (CPU 光栅图像)
│       ├── SkImage_Lazy (延迟生成图像)
│       ├── SkImage_Ganesh (Ganesh GPU 图像)
│       ├── SkImage_Graphite (Graphite GPU 图像)
│       └── ...其他变体
├── SkBitmapCache (位图缓存)
└── GPU 后端
```

## 主要类与结构体

### `SkImage_Base`
继承自 `SkImage`，为所有图像实现提供内部虚函数接口。

### `Type` 枚举
```cpp
enum class Type {
    kRaster, kRasterPinnable, kLazy, kLazyPicture, kLazyTexture,
    kGanesh, kGaneshYUVA, kGraphite, kGraphiteYUVA,
};
```
- 标识图像的具体实现类型，用于运行时类型判断。

### 辅助转换函数
```cpp
static inline SkImage_Base* as_IB(SkImage* image);
static inline const SkImage_Base* as_IB(const SkImage* image);
static inline SkImage_Base* as_IB(const sk_sp<SkImage>& image);
```
- 将公共 `SkImage` 安全地向下转换为 `SkImage_Base`，用于内部代码访问非公共接口。

## 公共 API 函数

### 纯虚函数 (子类必须实现)
- `onReadPixels()`: 从图像读取像素到指定的 SkImageInfo/buffer。
- `onHasMipmaps()`: 查询图像是否包含 mipmap。
- `onIsProtected()`: 查询图像是否受保护（GPU 安全内存）。
- `getROPixels()`: 获取只读的位图表示。
- `onMakeSubset()`: 创建图像的子集。
- `onMakeSurface()`: 创建适合该图像后端的渲染表面。
- `type()`: 返回图像的具体类型。
- `onReinterpretColorSpace()`: 在不转换像素数据的情况下重新解释颜色空间。

### 默认实现的虚函数
- `onPeekPixels()`: 直接访问像素数据（默认返回 false）。
- `onPeekBitmap()`: 直接访问底层位图（默认返回 nullptr）。
- `onPeekMips()`: 访问 mipmap 数据（默认返回 nullptr）。
- `context()` / `directContext()`: 获取 GPU 上下文（默认返回 nullptr）。
- `onRefEncoded()`: 获取编码后的图像数据（默认返回 nullptr）。
- `onMakeWithMipmaps()`: 创建带 mipmap 的图像副本（默认返回 nullptr）。

### 非虚方法
- `makeSubset()`: 公共的子集创建方法，进行边界验证后委托给 `onMakeSubset()`。
- `makeColorSpace()`: 委托给 `makeColorTypeAndColorSpace()`。
- `refMips()`: 返回 mipmap 的引用计数指针。

### 异步像素读取
- `onAsyncRescaleAndReadPixels()`: 异步缩放并读取像素。默认实现先读取像素到位图，然后调用 `SkRescaleAndReadPixels`。
- `onAsyncRescaleAndReadPixelsYUV420()`: 异步 YUV420 格式读取。默认实现直接以 nullptr 调用回调（TODO: 未完全实现）。

### 类型查询方法
- `isLazyGenerated()`: 是否为延迟生成（Picture-backed 或 Codec-backed）。
- `isRasterBacked()`: 是否为 CPU 光栅后端。
- `isGaneshBacked()`: 是否为 Ganesh GPU 后端。
- `isGraphiteBacked()`: 是否为 Graphite GPU 后端。
- `isYUVA()`: 是否为 YUVA 格式。
- `isTextureBacked()`: 是否为 GPU 纹理后端（Ganesh 或 Graphite）。

## 内部实现细节

### 位图缓存通知
```cpp
SkImage_Base::~SkImage_Base() {
    if (fAddedToRasterCache.load()) {
        SkNotifyBitmapGenIDIsStale(this->uniqueID());
    }
}
```
- 析构时检查是否被添加到光栅缓存中，如果是则通知缓存该图像 ID 已失效。
- 使用 `std::atomic<bool>` 保证线程安全。

### onAsLegacyBitmap 默认实现
将图像转换为 `kN32_SkColorType` 的位图，不使用颜色空间转换。这是一个后备实现，子类可以提供更优化的版本。

### makeSubset 边界验证
```cpp
sk_sp<SkImage> SkImage_Base::makeSubset(...) const {
    if (subset.isEmpty()) return nullptr;
    const SkIRect bounds = SkIRect::MakeWH(this->width(), this->height());
    if (!bounds.contains(subset)) return nullptr;
    return this->onMakeSubset(recorder, subset, requiredProps);
}
```
- 验证子集矩形非空且完全包含在图像边界内。

## 依赖关系

- `include/core/SkImage.h`: 公共基类。
- `include/core/SkData.h`: 编码数据。
- `src/core/SkMipmap.h`: Mipmap 管理。
- `src/core/SkBitmapCache.h`: 位图缓存通知。
- `src/image/SkRescaleAndReadPixels.h`: 异步缩放读取实现。
- `include/core/SkBitmap.h`, `SkPixmap.h`, `SkColorSpace.h` 等核心类型。

## 设计模式与设计决策

1. **模板方法模式**: 基类定义算法框架（如 `makeSubset` 的验证逻辑），子类实现具体步骤（`onMakeSubset`）。
2. **NVI (Non-Virtual Interface)**: 公共方法（如 `makeSubset`）是非虚的，执行验证后委托给受保护的虚方法。
3. **类型判别**: 使用 `Type` 枚举而非 `dynamic_cast` 进行类型判断，效率更高。
4. **缓存协作**: 通过 `notifyAddedToRasterCache()` 和析构通知机制与位图缓存系统协作，确保缓存一致性。

## 性能考量

1. **虚函数分派**: 所有后端特定操作通过虚函数分派，这是不可避免的但开销很小。
2. **原子操作**: `fAddedToRasterCache` 使用 `std::atomic<bool>`，析构时的 `load()` 操作开销极小。
3. **异步读取**: 提供异步 API 允许 GPU 后端利用异步传输，避免阻塞渲染管线。
4. **延迟生成**: `isLazyGenerated()` 类型的图像只在实际需要像素时才生成，节省内存和计算。

## 相关文件

- `include/core/SkImage.h`: 公共 SkImage API。
- `src/image/SkImage_Raster.h/.cpp`: CPU 光栅图像实现。
- `src/image/SkImage_Lazy.h/.cpp`: 延迟生成图像实现。
- `src/gpu/ganesh/image/SkImage_Ganesh.h/.cpp`: Ganesh GPU 图像实现。
- `src/core/SkBitmapCache.h`: 位图缓存管理。
- `src/image/SkRescaleAndReadPixels.h`: 异步缩放读取工具。
