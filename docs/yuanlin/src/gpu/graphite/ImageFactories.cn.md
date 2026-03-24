# ImageFactories

> 源文件
> - src/gpu/graphite/ImageFactories.cpp

## 概述

`ImageFactories.cpp` 实现了 Graphite 特定的 `SkImage` 工厂函数，用于从各种源创建GPU支持的图像。这些工厂函数是 `SkImage` 公共 API 的后端实现，处理纹理创建、数据上传和图像封装。

## 主要函数

### MakeFromBitmap

从 `SkBitmap` 创建 Graphite 图像：
```cpp
sk_sp<SkImage> SkImages::MakeFromBitmap(Recorder*,
                                       const SkBitmap&,
                                       sk_sp<SkMipmap>,
                                       Budgeted,
                                       SkImage::RequiredProperties);
```

### MakeFromRasterBitmap

从光栅位图创建：
```cpp
sk_sp<SkImage> SkImages::MakeFromRasterBitmap(Recorder*,
                                             const SkBitmap&,
                                             Mipmapped);
```

### MakeFromTexture

从现有纹理创建：
```cpp
sk_sp<SkImage> SkImages::MakeFromTexture(Recorder*,
                                        const BackendTexture&,
                                        SkColorType,
                                        SkAlphaType,
                                        sk_sp<SkColorSpace>);
```

### MakePromiseTexture

创建承诺纹理图像（延迟纹理提供）。

### MakeFromYUVATextures

从 YUVA 平面纹理创建。

## 实现细节

### 数据上传

工厂函数处理：
1. 纹理分配（通过 `ResourceProvider`）
2. 数据上传（通过 `UploadTask`）
3. Mipmap 生成（如果需要）

### 图像类型

创建不同的 `Image_Graphite` 子类：
- `Image_Graphite`：标准纹理图像
- `Image_YUVA_Graphite`：YUVA 格式图像

### 预算管理

支持 `Budgeted` 标志：
- `kYes`：计入GPU内存预算
- `kNo`：不计入预算（如临时资源）

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/gpu/graphite/Image_Graphite.h` | Graphite 图像实现 |
| `src/gpu/graphite/Image_YUVA_Graphite.h` | YUVA 图像实现 |
| `include/core/SkImage.h` | 公共图像 API |
| `include/gpu/graphite/Recorder.h` | 录制器（用于上传） |
| `src/gpu/graphite/ResourceProvider.h` | 资源提供者 |
