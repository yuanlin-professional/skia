# Surface_Graphite

> 源文件: src/gpu/graphite/Surface_Graphite.h, src/gpu/graphite/Surface_Graphite.cpp

## 概述

`Surface_Graphite` 是 Skia Graphite 渲染架构中 `SkSurface` 的 GPU 后端实现。该类封装了 Graphite 的 `Device` 对象，为客户端提供可绘制的 2D 画布表面，并管理底层的 GPU 纹理资源。Surface 是 Skia 绘图 API 的入口点，支持 Canvas 创建、图像快照、像素读写等操作。

## 架构位置

```
Skia Surface 架构：
  ├── SkSurface（公共 API）
  │   └── SkSurface_Base（内部基类）
  │       ├── Surface_Graphite（Graphite 实现）★
  │       ├── SkSurface_Ganesh（Ganesh 实现）
  │       └── SkSurface_Raster（光栅实现）
  └── Device（绘制目标）
      └── TextureProxy（GPU 纹理代理）
```

## 主要类与结构体

### Surface 类

```cpp
class Surface final : public SkSurface_Base {
public:
    // 创建常规 Surface（注册到 Recorder）
    static sk_sp<Surface> Make(Recorder* recorder,
                              const SkImageInfo& info,
                              std::string_view label,
                              Budgeted budgeted,
                              Mipmapped mipmapped,
                              SkBackingFit backingFit,
                              const SkSurfaceProps* props);

    // 创建临时 Surface（不注册，手动刷新）
    static sk_sp<Surface> MakeScratch(Recorder* recorder,
                                     const SkImageInfo& info,
                                     std::string_view label,
                                     Budgeted budgeted,
                                     Mipmapped mipmapped,
                                     SkBackingFit backingFit);

    Surface(sk_sp<Device> device);
    ~Surface() override;

    SkImageInfo imageInfo() const override;
    Recorder* onGetRecorder() const override;
    SkCanvas* onNewCanvas() override;
    sk_sp<SkSurface> onNewSurface(const SkImageInfo&) override;
    sk_sp<SkImage> onNewImageSnapshot(const SkIRect* subset) override;
    void onWritePixels(const SkPixmap&, int x, int y) override;

    // Graphite 特定接口
    TextureProxyView readSurfaceView() const;
    sk_sp<Image> asImage() const;
    sk_sp<Image> asImage(SkColorType otherCT, SkAlphaType otherAT) const;
    sk_sp<Image> makeImageCopy(const SkIRect* subset, Mipmapped) const;
    TextureProxy* backingTextureProxy() const;
    void flushToDrawContext(DrawContext*);

private:
    sk_sp<Device> fDevice;    // 绘制设备
    sk_sp<Image> fImageView;  // 关联的图像视图
};
```

## 公共 API 函数

### Make 工厂函数

```cpp
static sk_sp<Surface> Make(Recorder* recorder,
                          const SkImageInfo& info,
                          std::string_view label,
                          Budgeted budgeted,
                          Mipmapped mipmapped,
                          SkBackingFit backingFit,
                          const SkSurfaceProps* props);
```

**功能**: 创建可绘制的 GPU Surface，自动注册到 Recorder。

**参数**: recorder（命令录制器）、info（图像信息）、label（调试标签）、budgeted（是否计入预算）、mipmapped（是否生成 mipmap）、backingFit（纹理尺寸匹配模式）、props（Surface 属性）。

### MakeScratch 工厂函数

```cpp
static sk_sp<Surface> MakeScratch(...);
```

**功能**: 创建临时 Surface，不自动注册到 Recorder，需要手动刷新。适用于短期使用的临时渲染目标。

### asImage

```cpp
sk_sp<Image> asImage() const;
sk_sp<Image> asImage(SkColorType otherCT, SkAlphaType otherAT) const;
```

**功能**: 返回 Surface 的图像视图，共享底层纹理。第二个重载允许使用不同的颜色类型和 alpha 类型。

### makeImageCopy

```cpp
sk_sp<Image> makeImageCopy(const SkIRect* subset, Mipmapped mipmapped) const;
```

**功能**: 创建 Surface 的图像副本，可选择子区域和 mipmap 生成。

### flushToDrawContext

```cpp
void flushToDrawContext(DrawContext* drawContext);
```

**功能**: 将 Surface 的待处理绘制命令刷新到指定的 DrawContext。

## 内部实现细节

### 构造和析构

```cpp
Surface::Surface(sk_sp<Device> device)
    : SkSurface_Base(device->width(), device->height(), &device->surfaceProps())
    , fDevice(std::move(device))
    , fImageView(Image::WrapDevice(fDevice)) {}

Surface::~Surface() {
    fDevice->setImmutable();  // 标记设备为不可变，触发刷新
}
```

**关键点**: 析构时标记设备为不可变，确保所有待处理工作被刷新，并允许关联的图像视图分离。

### 图像快照

```cpp
sk_sp<SkImage> Surface::onNewImageSnapshot(const SkIRect* subset) {
    return this->makeImageCopy(subset, fDevice->target()->mipmapped());
}
```

**行为**: 创建纹理副本而非共享视图，确保快照不受后续绘制影响。

### 写入像素

```cpp
void Surface::onWritePixels(const SkPixmap& pixmap, int x, int y) {
    fDevice->writePixels(pixmap, x, y);
}
```

**委托模式**: 所有绘制操作委托给内部 `Device` 对象。

### API 兼容性警告

```cpp
if (this->hasCachedImage()) {
    SKGPU_LOG_W("Intermingling makeImageSnapshot and asImage calls may produce "
                "unexpected results. Please use either the old _or_ new API.");
}
```

**设计决策**: 警告混用旧 API（`makeImageSnapshot`）和新 API（`asImage`），避免意外行为。

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `SkSurface_Base` | 抽象基类 |
| `Device` | 绘制设备和纹理管理 |
| `Image` | 图像视图 |
| `Recorder` | 命令录制器 |
| `TextureProxy` | 纹理代理 |
| `DrawContext` | 绘制上下文 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `SkSurface` 公共 API | Surface 创建和操作 |
| 客户端应用 | 绘图操作 |

## 设计模式与设计决策

### 外观模式

Surface 为复杂的 Device 和 TextureProxy 提供简单接口，隐藏 GPU 细节。

### 委托模式

所有绘制操作委托给内部 Device，Surface 仅管理生命周期和 API 适配。

### 共享视图 vs 拷贝

- `asImage()`: 共享纹理，零拷贝，但后续绘制会影响图像
- `makeImageSnapshot()`: 拷贝纹理，隔离变化，但有内存开销

### 关键设计决策

1. **Device 包装**: Surface 包装 Device 而非直接管理纹理
2. **自动刷新**: 析构时自动标记设备为不可变
3. **图像视图缓存**: fImageView 避免重复创建图像对象
4. **Scratch Surface**: 支持短期临时 Surface，不注册到 Recorder

## 性能考量

### 内存管理

1. **共享纹理**: `asImage()` 零拷贝，多个图像可共享纹理
2. **智能指针**: 使用 `sk_sp` 自动管理生命周期
3. **延迟拷贝**: 仅在 `makeImageSnapshot()` 时才拷贝纹理

### 绘制性能

1. **命令批处理**: 绘制命令批处理到 DrawContext
2. **自动刷新**: 析构时自动刷新，确保命令提交
3. **Scratch Surface**: 临时 Surface 减少 Recorder 注册开销

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/image/SkSurface_Base.h` | Surface 基类 |
| `src/gpu/graphite/Device.h` | Graphite 绘制设备 |
| `src/gpu/graphite/Image_Graphite.h` | Graphite 图像实现 |
| `src/gpu/graphite/Recorder.h` | 命令录制器 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `include/gpu/graphite/Surface.h` | 公共 Surface API |
