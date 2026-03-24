# SkImage_LazyFactories

> 源文件：src/image/SkImage_LazyFactories.cpp

## 概述

`SkImage_LazyFactories.cpp` 实现了创建延迟加载（Lazy）Picture 图像的工厂函数。这些函数将 `SkPicture` 矢量图形对象包装为 `SkImage`，实现延迟栅格化。

## 主要函数

### DeferredFromPicture（两个重载）

**基础版本**：
```cpp
sk_sp<SkImage> DeferredFromPicture(sk_sp<SkPicture> picture,
                                   const SkISize& dimensions,
                                   const SkMatrix* matrix,
                                   const SkPaint* paint,
                                   BitDepth bitDepth,
                                   sk_sp<SkColorSpace> colorSpace) {
    return SkImage_Picture::Make(std::move(picture), dimensions, matrix, paint,
                                 bitDepth, std::move(colorSpace), {});  // 空 SurfaceProps
}
```

**完整版本**（带 SurfaceProps）：
```cpp
sk_sp<SkImage> DeferredFromPicture(sk_sp<SkPicture> picture,
                                   const SkISize& dimensions,
                                   const SkMatrix* matrix,
                                   const SkPaint* paint,
                                   BitDepth bitDepth,
                                   sk_sp<SkColorSpace> colorSpace,
                                   SkSurfaceProps props) {
    return SkImage_Picture::Make(std::move(picture), dimensions, matrix, paint,
                                 bitDepth, std::move(colorSpace), props);
}
```

## 功能说明

### 参数

- `picture`：要包装的 Picture 对象
- `dimensions`：目标图像尺寸
- `matrix`：可选的变换矩阵
- `paint`：可选的绘制参数
- `bitDepth`：位深度（`kU8` 或 `kF16`）
- `colorSpace`：颜色空间
- `props`：表面属性（影响文本渲染）

### 延迟栅格化

图像创建时不栅格化 Picture，仅在需要像素数据时才执行绘制。

## 设计模式

### 外观模式

简化的工厂函数隐藏了 `SkImage_Picture::Make()` 的复杂性。

### 重载设计

提供默认参数版本和完整参数版本，满足不同使用场景。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/image/SkImage_Picture.h` | 实现类 | Picture 图像实现 |
| `include/core/SkPicture.h` | 数据源 | Picture 接口 |
| `include/core/SkImage.h` | API | 图像公共接口 |
