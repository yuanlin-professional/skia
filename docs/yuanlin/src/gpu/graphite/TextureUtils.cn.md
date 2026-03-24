# TextureUtils

> 源文件: src/gpu/graphite/TextureUtils.h, src/gpu/graphite/TextureUtils.cpp

## 概述

`TextureUtils` 是 Skia Graphite 渲染架构中提供纹理操作辅助函数的工具模块。该模块包含纹理上传、数据拷贝、图像转换、mipmap 生成以及纹理大小计算等实用函数。它是 Graphite 纹理系统的工具箱，被图像创建、Surface 操作和数据传输等模块广泛使用。

## 架构位置

```
Graphite 纹理工具：
  ├── TextureUtils（辅助函数集）★
  │   ├── 数据上传
  │   ├── 图像转换
  │   ├── Mipmap 生成
  │   └── 大小计算
  ├── Texture / TextureProxy
  ├── Image
  └── Surface
```

## 主要函数

### 纹理大小计算

```cpp
size_t ComputeSize(SkISize dimensions, const TextureInfo& info);
```

计算纹理占用的 GPU 内存大小，包含 mipmap 和多重采样开销。

### 图像上传

```cpp
bool UploadFromCpuToGpu(Recorder* recorder,
                       sk_sp<TextureProxy> textureProxy,
                       const SkColorInfo& srcColorInfo,
                       const SkColorInfo& dstColorInfo,
                       const std::vector<MipLevel>& levels,
                       const SkIRect& dstRect);
```

将 CPU 侧像素数据上传到 GPU 纹理。

### 图像转换

```cpp
std::tuple<sk_sp<Image>, SkSamplingOptions>
GetGraphiteBacked(Recorder* recorder,
                 const SkImage* image,
                 SkSamplingOptions sampling);
```

将任意后端的图像转换为 Graphite 后端图像。

### Mipmap 生成

```cpp
sk_sp<TextureProxy> GenerateMipmaps(Recorder* recorder,
                                   sk_sp<TextureProxy> texture,
                                   const SkColorInfo& colorInfo);
```

为纹理生成 mipmap 级别链。

### 数据读回

```cpp
bool ReadPixelsWithCopy(Recorder* recorder,
                       const TextureProxy* srcProxy,
                       const SkColorInfo& srcColorInfo,
                       const SkColorInfo& dstColorInfo,
                       const SkIRect& srcRect,
                       SkPixmap dstPixmap);
```

从 GPU 纹理读取像素数据到 CPU。

## 内部实现细节

### 纹理大小计算

```cpp
size_t ComputeSize(SkISize dimensions, const TextureInfo& info) {
    size_t size = dimensions.width() * dimensions.height() * info.bytesPerPixel();
    if (info.mipmapped() == Mipmapped::kYes) {
        size += size / 3;  // mipmap chain ≈ 1.33x
    }
    size *= info.sampleCount();
    return size;
}
```

### 上传策略

1. **直接上传**: 主机端可写纹理（如 Metal Shared）
2. **通过缓冲区**: 大多数情况，先写缓冲区再拷贝到纹理

### 图像转换流程

1. 检查图像是否已经是 Graphite 后端
2. 如果不是，创建新纹理并上传数据
3. 使用 `ImageProvider` 允许自定义转换逻辑

### Mipmap 生成

使用计算着色器或渲染通道逐级生成 mipmap：
```cpp
for (int level = 1; level < maxLevel; ++level) {
    // 从 level-1 下采样到 level
    BlitMipLevel(recorder, srcLevel, dstLevel);
}
```

## 依赖关系

### 内部依赖

| 依赖类 | 用途 |
|--------|------|
| `Texture / TextureProxy` | 纹理对象 |
| `Recorder` | 命令录制 |
| `UploadBufferManager` | 上传缓冲区管理 |
| `TextureInfo` | 纹理格式信息 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `Image_Graphite` | 图像创建和转换 |
| `Surface_Graphite` | 像素写入和读取 |
| `Device` | 纹理操作 |

## 设计模式与设计决策

### 工具函数模块

提供独立的辅助函数，无状态，易于测试。

### 策略模式

根据纹理特性选择上传策略：
- 主机端可写 → 直接写入
- 普通纹理 → 通过缓冲区

### 关键设计决策

1. **命名空间函数**: 避免创建工具类实例
2. **多路径上传**: 支持不同后端的最优上传方式
3. **格式转换**: 自动处理颜色空间和像素格式转换
4. **Mipmap 链生成**: 利用 GPU 加速下采样

## 性能考量

### 上传优化

1. **批处理**: 多个 mip 级别一次上传
2. **缓冲区复用**: 重用上传缓冲区
3. **主机端写入**: 避免额外拷贝（UMA 架构）

### Mipmap 生成

1. **GPU 加速**: 使用计算着色器或渲染
2. **延迟生成**: 仅在需要时生成
3. **级联下采样**: 从低级别生成高级别

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/Texture.h` | 纹理类 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `src/gpu/graphite/Image_Graphite.h` | Graphite 图像 |
| `src/gpu/graphite/UploadBufferManager.h` | 上传缓冲管理 |
| `src/gpu/graphite/Recorder.h` | 命令录制器 |
