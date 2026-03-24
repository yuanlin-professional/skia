# SkImage_AndroidFactories — Android 平台图像工厂

> 源文件: `src/image/SkImage_AndroidFactories.cpp`

## 概述

`SkImage_AndroidFactories.cpp` 提供了专门为 Android 平台设计的 `SkImage` 工厂函数。当前仅包含一个函数 `RasterFromBitmapNoCopy`，该函数从 `SkBitmap` 创建光栅图像，但保证不复制像素数据。

这个"零拷贝"特性对于 Android 平台特别重要，因为 Android 系统中的位图通常由底层内存管理器（如 AHardwareBuffer）管理，拷贝像素不仅浪费内存，还可能破坏共享内存的语义。

## 架构位置

```
Skia
├── include/android/
│   └── SkImageAndroid.h                // Android 图像 API 声明
├── src/image/
│   ├── SkImage_AndroidFactories.cpp    // 本文件
│   ├── SkImage_Raster.h               // 光栅图像实现类
│   └── SkImage_Raster.cpp             // 光栅图像实现
```

该文件属于 Skia 的 Android 平台特定层，为 Android 应用提供高效的图像创建路径。

## 主要类与结构体

本文件不定义任何类或结构体。

## 公共 API 函数

### `sk_sp<SkImage> SkImages::RasterFromBitmapNoCopy(const SkBitmap& bm)`

- **功能**: 从 `SkBitmap` 创建光栅 `SkImage`，保证不复制像素数据
- **参数**: `bm` — 源位图
- **返回值**: 成功返回共享像素数据的 `SkImage`；如果位图无效或不可共享则返回 `nullptr`
- **关键行为**: 使用 `SkCopyPixelsMode::kNever` 模式，确保永不拷贝像素。如果位图的像素不能被直接共享（例如可变位图），函数会返回 `nullptr` 而不是回退到拷贝
- **线程安全**: 返回的 `SkImage` 是不可变的，可以安全地在线程间共享

## 内部实现细节

实现委托给 `SkImage_Raster::MakeFromBitmap(bm, SkCopyPixelsMode::kNever)`：

- `SkCopyPixelsMode::kNever` 告诉 `MakeFromBitmap` 在无法共享像素时返回失败，而非回退到拷贝
- 与默认的 `SkImages::RasterFromBitmap`（允许拷贝）形成对比

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `include/android/SkImageAndroid.h` | API 声明 |
| `include/core/SkBitmap.h` | 位图类 |
| `src/image/SkImage_Raster.h` | 光栅图像实现（`MakeFromBitmap`） |

## 设计模式与设计决策

1. **平台特定工厂**: 将 Android 特定的工厂函数放在独立文件中，通过编译系统控制是否链接
2. **明确的零拷贝语义**: 使用 `kNever` 模式明确表达"绝不拷贝"的意图，避免意外的性能退化
3. **命名空间组织**: 放在 `SkImages` 命名空间中，与其他图像工厂函数保持一致

## 性能考量

- 零拷贝设计避免了可能较大的像素数据拷贝
- 函数本身仅涉及引用计数操作和少量指针操作
- 对于 Android 上的高频图像创建场景（如列表滚动中的缩略图加载），零拷贝可以显著降低内存带宽压力

## 相关文件

- `include/android/SkImageAndroid.h` — Android 图像 API 声明
- `src/image/SkImage_Raster.h` — 光栅图像类
- `src/image/SkImage_Raster.cpp` — 光栅图像实现
- `include/core/SkBitmap.h` — 位图类
- `include/core/SkImage.h` — 图像基类
