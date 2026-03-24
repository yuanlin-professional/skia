# SkKeyedImage

> 源文件
> - src/pdf/SkKeyedImage.h
> - src/pdf/SkKeyedImage.cpp

## 概述

`SkKeyedImage` 是 Skia PDF 模块中用于图像管理的轻量级包装类，结合了 `SkImage` 和 `SkBitmap` 的优点。它通过 `SkBitmapKey` 提供去重能力，同时保持对编码数据的引用，优化 PDF 文档中图像资源的管理。

主要特性：
1. **智能去重**：通过 `SkBitmapKey` 识别相同或子集图像，避免重复嵌入
2. **编码数据保持**：`SkImage` 保留原始编码数据，减少内存使用
3. **子集支持**：高效创建图像子集而不复制像素数据
4. **统一接口**：同时支持从 `SkImage` 和 `SkBitmap` 构造

## 架构位置

`SkKeyedImage` 位于 PDF 模块的资源管理层：

```
src/pdf/
├── SkPDFDevice.cpp          // PDF 设备，使用 SkKeyedImage 管理图像
├── SkPDFBitmap.cpp          // PDF 位图处理
├── SkBitmapKey.h            // 位图键定义
├── SkKeyedImage.h/cpp       // 带键的图像（当前模块）
└── SkPDFDocument.cpp        // PDF 文档，管理图像资源
```

它作为 Skia 图像系统和 PDF 资源系统之间的桥梁。

## 主要类与结构体

### SkKeyedImage

**构造函数:**
```cpp
SkKeyedImage();                        // 默认构造（空图像）
explicit SkKeyedImage(sk_sp<SkImage>); // 从 SkImage 构造
explicit SkKeyedImage(const SkBitmap&); // 从 SkBitmap 构造
```

**特殊成员函数:**
```cpp
SkKeyedImage(SkKeyedImage&&) = default;           // 移动构造
SkKeyedImage(const SkKeyedImage&) = default;      // 拷贝构造
SkKeyedImage& operator=(SkKeyedImage&&) = default; // 移动赋值
SkKeyedImage& operator=(const SkKeyedImage&) = default; // 拷贝赋值
```
使用默认实现，依赖 `sk_sp` 的智能指针语义。

**成员变量:**
```cpp
sk_sp<SkImage> fImage;                      // 图像智能指针
SkBitmapKey fKey = {{0, 0, 0, 0}, 0};      // 图像键
```

**公共方法:**
```cpp
explicit operator bool() const { return fImage != nullptr; }
const SkBitmapKey& key() const { return fKey; }
const sk_sp<SkImage>& image() const { return fImage; }
sk_sp<SkImage> release();
SkKeyedImage subset(SkIRect subset) const;
```

### SkBitmapKey

定义在 `SkBitmapKey.h`，结构如下：
```cpp
struct SkBitmapKey {
    SkIRect fSubset;      // 子集矩形
    uint32_t fID;         // 生成 ID 或唯一 ID
};
```

## 公共 API 函数

### 构造函数

**从 SkImage 构造:**
```cpp
SkKeyedImage::SkKeyedImage(sk_sp<SkImage> i) : fImage(std::move(i)) {
    fKey = SkBitmapKeyFromImage(fImage.get());
}
```
- 使用移动语义避免引用计数操作
- 调用 `SkBitmapKeyFromImage()` 生成键

**从 SkBitmap 构造:**
```cpp
SkKeyedImage::SkKeyedImage(const SkBitmap& bm) : fImage(bm.asImage()) {
    if (fImage) {
        fKey = {bm.getSubset(), bm.getGenerationID()};
    }
}
```
- 转换为 `SkImage` 以保持一致性
- 使用 Bitmap 的子集和生成 ID 构建键

### subset()

```cpp
SkKeyedImage subset(SkIRect subset) const;
```

**功能：**
- 创建当前图像的子集
- 不复制像素数据，仅创建新的视图
- 更新键中的子集矩形

**实现：**
```cpp
SkKeyedImage SkKeyedImage::subset(SkIRect subset) const {
    SkKeyedImage img;
    if (fImage && subset.intersect(fImage->bounds())) {
        img.fImage = fImage->makeSubset(nullptr, subset, {});
        if (img.fImage) {
            img.fKey = {subset.makeOffset(fKey.fSubset.topLeft()), fKey.fID};
        }
    }
    return img;
}
```

**关键步骤：**
1. 与原图像边界求交，确保子集有效
2. 调用 `SkImage::makeSubset()` 创建子集视图
3. 计算新的子集矩形（相对于原始位图的坐标）
4. 保持相同的 ID，因为底层数据未变

### release()

```cpp
sk_sp<SkImage> release();
```

**功能：**
- 释放并返回图像智能指针
- 重置键为空状态
- 类似 `std::unique_ptr::release()`

**实现：**
```cpp
sk_sp<SkImage> SkKeyedImage::release() {
    sk_sp<SkImage> image = std::move(fImage);
    SkASSERT(nullptr == fImage);  // 确保已移动
    fKey = {{0, 0, 0, 0}, 0};     // 重置键
    return image;
}
```

### SkBitmapKeyFromImage()

```cpp
SkBitmapKey SkBitmapKeyFromImage(const SkImage* image);
```

**功能：**
- 从 `SkImage` 生成 `SkBitmapKey`
- 处理 `SkImage` 包装 `SkBitmap` 的特殊情况

**实现：**
```cpp
SkBitmapKey SkBitmapKeyFromImage(const SkImage* image) {
    if (!image) {
        return {{0, 0, 0, 0}, 0};
    }
    if (const SkBitmap* bm = as_IB(image)->onPeekBitmap()) {
        SkIPoint o = bm->pixelRefOrigin();
        return {image->bounds().makeOffset(o), bm->getGenerationID()};
    }
    return {image->bounds(), image->uniqueID()};
}
```

**两种情况：**
1. **Image 包装 Bitmap**：使用 Bitmap 的生成 ID 和 pixelRef 原点
2. **纯 Image**：使用 Image 的唯一 ID 和边界

## 内部实现细节

### 键的生成逻辑

**SkBitmap 的 GenerationID vs SkImage 的 UniqueID：**
- `GenerationID`：Bitmap 的 pixelRef 生成 ID，相同数据具有相同 ID
- `UniqueID`：Image 的唯一标识符，即使数据相同也可能不同

**子集坐标计算：**
```cpp
subset.makeOffset(fKey.fSubset.topLeft())
```
子集矩形需要相对于原始位图的全局坐标，而非当前图像的局部坐标。

**示例：**
```
原始 Bitmap: bounds = (0, 0, 100, 100), generationID = 123
第一次子集: subset = (10, 10, 50, 50)
  -> key = {(10, 10, 50, 50), 123}
第二次子集: subset = (5, 5, 30, 30)  // 相对于第一次子集
  -> key = {(15, 15, 40, 40), 123}   // 相对于原始 Bitmap
```

### SkImage 内部的 Bitmap

```cpp
if (const SkBitmap* bm = as_IB(image)->onPeekBitmap())
```

`as_IB()` 将 `SkImage` 转换为 `SkImage_Base`，访问内部实现：
- 如果 Image 是从 Bitmap 创建的，返回底层 Bitmap
- 否则返回 nullptr

这允许在 Bitmap -> Image 转换后仍能使用 Bitmap 的去重能力。

### 智能指针语义

```cpp
sk_sp<SkImage> fImage;
```

使用 `sk_sp`（Skia 的智能指针）：
- 自动管理引用计数
- 拷贝 `SkKeyedImage` 时共享底层图像数据
- 移动 `SkKeyedImage` 时无需修改引用计数

## 依赖关系

**直接依赖:**
```cpp
#include "include/core/SkImage.h"    // SkImage 类型
#include "include/core/SkBitmap.h"   // SkBitmap 类型
#include "src/pdf/SkBitmapKey.h"     // SkBitmapKey 定义
#include "src/image/SkImage_Base.h"  // SkImage 内部实现
```

**被依赖:**
```cpp
src/pdf/SkPDFDevice.cpp              // 使用 SkKeyedImage 管理图像
src/pdf/SkPDFBitmap.cpp              // 处理 SkKeyedImage
src/pdf/SkPDFDocument.cpp            // 文档级图像去重
```

## 设计模式与设计决策

### 1. 值语义与资源管理

`SkKeyedImage` 是一个值类型：
- 支持拷贝和移动
- 底层图像通过智能指针共享
- 轻量级，可以按值传递

### 2. 组合优于继承

不继承 `SkImage` 或 `SkBitmap`，而是组合它们：
- 避免虚函数开销
- 保持简单的接口
- 便于添加键管理逻辑

### 3. 双重接口支持

同时支持 `SkImage` 和 `SkBitmap` 输入：
- `SkImage`：现代 API，支持 GPU 和编码数据
- `SkBitmap`：传统 API，更精细的内存控制

PDF 生成可能从两种来源获取图像，统一接口简化调用。

### 4. 延迟去重

`SkKeyedImage` 只负责生成键，实际去重由 PDF 文档管理器完成：
- 分离关注点
- 支持全局去重策略
- 避免在 `SkKeyedImage` 中维护缓存

### 5. 子集的写时拷贝

```cpp
img.fImage = fImage->makeSubset(nullptr, subset, {});
```

`SkImage::makeSubset()` 通常不复制像素：
- 对于光栅图像，可能只是调整元数据
- 对于 GPU 图像，创建纹理视图
- 真正的拷贝发生在必要时（写时拷贝）

## 性能考量

### 1. 零拷贝子集

子集操作不复制像素数据：
- 节省内存
- 避免 CPU 拷贝时间
- 对大图像尤其重要

### 2. 引用计数优化

```cpp
SkKeyedImage(sk_sp<SkImage> i) : fImage(std::move(i))
```
使用移动语义避免不必要的引用计数原子操作。

### 3. 编码数据保持

`SkImage` 可以保持原始编码数据（如 JPEG）：
- 避免解码和重新编码
- 直接嵌入 PDF，减小文件大小
- 提高性能

### 4. 键的轻量级比较

`SkBitmapKey` 只有两个字段（矩形和 ID）：
- 比较快速（一次整数比较 + 四次坐标比较）
- 适合用作哈希表的键

## 相关文件

| 文件路径 | 说明 | 关系 |
|---------|------|------|
| `src/pdf/SkBitmapKey.h` | 位图键定义 | 核心依赖 |
| `include/core/SkImage.h` | 图像接口 | 包装对象 |
| `include/core/SkBitmap.h` | 位图接口 | 替代输入 |
| `src/image/SkImage_Base.h` | 图像内部实现 | 访问底层 Bitmap |
| `src/pdf/SkPDFDevice.cpp` | PDF 设备 | 主要使用者 |
| `src/pdf/SkPDFBitmap.cpp` | PDF 位图处理 | 处理图像数据 |
| `src/pdf/SkPDFDocument.cpp` | PDF 文档 | 图像去重管理 |
| `include/core/SkRefCnt.h` | 引用计数 | sk_sp 基础 |
