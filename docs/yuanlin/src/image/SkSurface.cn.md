# SkSurface

> 源文件：src/image/SkSurface.cpp

## 概述

`SkSurface.cpp` 实现了 `SkSurface` 公共 API 和 `SkSurfaceProps` 的构造函数。它提供了表面对象的统一外部接口，将调用委托给内部基类 `SkSurface_Base` 的虚函数实现。文件还包含了参数验证、边界检查、异步读取像素等通用功能。

该文件是表面系统的公共入口，处理了 API 层的参数检查和类型转换，确保所有表面操作都经过正确的验证。

## 架构位置

- **API 层**：实现公共头文件 `include/core/SkSurface.h` 的函数
- **委托模式**：通过 `asSB()` 转换为 `SkSurface_Base` 并调用虚函数
- **辅助类**：`SkSurfaceProps` 的实现也在此文件

## 主要实现

### SkSurfaceProps 构造函数

```cpp
SkSurfaceProps::SkSurfaceProps()
    : fFlags(0)
    , fPixelGeometry(kUnknown_SkPixelGeometry)
    , fTextContrast(SK_GAMMA_CONTRAST)
    , fTextGamma(SK_GAMMA_EXPONENT) {}

SkSurfaceProps::SkSurfaceProps(uint32_t flags, SkPixelGeometry pg, ...)
    : fFlags(flags), fPixelGeometry(pg), ... {}
```

### SkSurface 构造函数

```cpp
SkSurface::SkSurface(int width, int height, const SkSurfaceProps* props)
    : fProps(SkSurfacePropsCopyOrDefault(props)), fWidth(width), fHeight(height) {
    fGenerationID = 0;  // 延迟分配
}
```

### 核心委托函数

**Canvas 访问**：
```cpp
SkCanvas* SkSurface::getCanvas() {
    return asSB(this)->getCachedCanvas();
}
```

**图像快照**：
```cpp
sk_sp<SkImage> SkSurface::makeImageSnapshot() {
    return asSB(this)->refCachedImage();
}

sk_sp<SkImage> SkSurface::makeImageSnapshot(const SkIRect& srcBounds) {
    // 边界检查
    if (!bounds.intersect(surfBounds)) return nullptr;
    if (bounds == surfBounds) {
        return this->makeImageSnapshot();
    } else {
        return asSB(this)->onNewImageSnapshot(&bounds);
    }
}
```

**像素读取**：
```cpp
bool SkSurface::readPixels(const SkPixmap& pm, int srcX, int srcY) {
    return this->getCanvas()->readPixels(pm, srcX, srcY);
}
```

**像素写入**：
```cpp
void SkSurface::writePixels(const SkPixmap& pmap, int x, int y) {
    // 参数验证
    if (pmap.addr() == nullptr || pmap.width() <= 0 || pmap.height() <= 0) {
        return;
    }
    // 边界检查
    if (!SkIRect::Intersects(srcR, dstR)) {
        return;
    }
    // 确定内容变化模式
    ContentChangeMode mode = srcR.contains(dstR) ? kDiscard : kRetain;
    // COW 处理并写入
    if (asSB(this)->aboutToDraw(mode)) {
        asSB(this)->onWritePixels(pmap, x, y);
    }
}
```

### 异步像素读取

**RGB 读取**：
```cpp
void SkSurface::asyncRescaleAndReadPixels(const SkImageInfo& info,
                                          const SkIRect& srcRect,
                                          RescaleGamma rescaleGamma,
                                          RescaleMode rescaleMode,
                                          ReadPixelsCallback callback,
                                          ReadPixelsContext context) {
    // 验证参数
    if (!SkIRect::MakeWH(this->width(), this->height()).contains(srcRect) ||
        !SkImageInfoIsValid(info)) {
        callback(context, nullptr);
        return;
    }
    // 委托给基类实现
    asSB(this)->onAsyncRescaleAndReadPixels(...);
}
```

**YUV420 读取**：
```cpp
void SkSurface::asyncRescaleAndReadPixelsYUV420(...) {
    // 验证：尺寸必须为偶数
    if (dstSize.isZero() || (dstSize.width() & 0b1) || (dstSize.height() & 0b1)) {
        callback(context, nullptr);
        return;
    }
    asSB(this)->onAsyncRescaleAndReadPixelsYUV420(...);
}
```

### 生成 ID 管理

```cpp
uint32_t SkSurface::generationID() {
    if (0 == fGenerationID) {
        fGenerationID = asSB(this)->newGenerationID();
    }
    return fGenerationID;
}
```

## 设计模式与设计决策

### 外观模式（Facade Pattern）

`SkSurface` 提供简洁的公共 API，隐藏内部复杂性。

### 决策 1：所有读取委托给 Canvas

```cpp
bool SkSurface::readPixels(...) {
    return this->getCanvas()->readPixels(...);
}
```

- **原因**：Canvas 已经实现了像素读取逻辑
- **优势**：代码复用，减少重复

### 决策 2：writePixels 智能检测内容变化模式

```cpp
ContentChangeMode mode = kRetain_ContentChangeMode;
if (srcR.contains(dstR)) {
    mode = kDiscard_ContentChangeMode;  // 完全覆盖，可丢弃旧内容
}
```

- **优化**：完全覆盖时避免不必要的数据保留

### 决策 3：YUV420 要求偶数尺寸

```cpp
if ((dstSize.width() & 0b1) || (dstSize.height() & 0b1)) {
    callback(context, nullptr);
}
```

- **原因**：YUV420 色度采样要求 2×2 像素块

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkSurface.h` | 头文件 | 公共 API 声明 |
| `src/image/SkSurface_Base.h` | 基类 | 内部实现基类 |
| `include/core/SkSurfaceProps.h` | 辅助类 | 表面属性定义 |
