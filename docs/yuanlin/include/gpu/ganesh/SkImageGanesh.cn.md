# SkImageGanesh

> 源文件: `include/gpu/ganesh/SkImageGanesh.h`

## 概述
SkImageGanesh 提供了基于 Ganesh GPU 后端创建和操作 SkImage 的工厂函数集合。该模块是 Skia 图像系统与 Ganesh GPU 渲染管线之间的桥梁,支持从 GPU 纹理、压缩数据、YUV 平面等多种来源创建 GPU 加速的图像对象。

## 架构位置
该文件位于 `include/gpu/ganesh` 公共 API 层,属于 Ganesh GPU 后端的图像处理子系统。它依赖核心的 SkImage 抽象,并与 GrRecordingContext/GrDirectContext 紧密集成,为上层应用提供 GPU 图像创建能力。

## 命名空间结构

### SkImages 命名空间
所有工厂函数都封装在 `SkImages` 命名空间中,遵循 Skia 的现代 API 设计模式,避免类成员函数的形式,提供更清晰的函数式 API。

## 核心类型定义

### 回调函数类型

#### BackendTextureReleaseProc
```cpp
using BackendTextureReleaseProc = std::function<void(GrBackendTexture)>;
```
- **用途**: 当后端纹理可以安全释放时被调用
- **参数**: GrBackendTexture - 被释放的纹理对象
- **使用场景**: 配合 MakeBackendTextureFromImage 使用

#### TextureReleaseProc
```cpp
using TextureReleaseProc = void (*)(ReleaseContext);
```
- **用途**: 传统 C 风格回调,当纹理可以释放时调用
- **参数**: ReleaseContext - 用户自定义上下文指针
- **使用场景**: BorrowTextureFrom, TextureFromCompressedTexture 等函数

## 公共 API 函数

### 从后端纹理创建图像

#### `AdoptTextureFrom`
```cpp
SK_API sk_sp<SkImage> AdoptTextureFrom(
    GrRecordingContext* context,
    const GrBackendTexture& backendTexture,
    GrSurfaceOrigin textureOrigin,
    SkColorType colorType,
    SkAlphaType alphaType = kPremul_SkAlphaType,
    sk_sp<SkColorSpace> colorSpace = nullptr);
```
- **功能**: 采用所有权模式从 GPU 纹理创建图像,Skia 接管纹理生命周期管理
- **参数**:
  - `context`: GPU 上下文
  - `backendTexture`: 后端纹理对象
  - `textureOrigin`: 纹理原点(上左或下左)
  - `colorType`: 像素颜色类型
  - `alphaType`: Alpha 类型(预乘或非预乘)
  - `colorSpace`: 色彩空间,可选
- **返回值**: 成功返回 SkImage,失败返回 nullptr
- **所有权**: Skia 负责释放纹理

#### `BorrowTextureFrom`
```cpp
SK_API sk_sp<SkImage> BorrowTextureFrom(
    GrRecordingContext* context,
    const GrBackendTexture& backendTexture,
    GrSurfaceOrigin origin,
    SkColorType colorType,
    SkAlphaType alphaType,
    sk_sp<SkColorSpace> colorSpace,
    TextureReleaseProc textureReleaseProc = nullptr,
    ReleaseContext releaseContext = nullptr);
```
- **功能**: 借用模式创建图像,纹理所有权保留在客户端
- **关键差异**: 客户端必须确保纹理在 SkImage 生命周期内有效
- **回调机制**: 通过 textureReleaseProc 通知客户端 Skia 不再使用纹理
- **DDL 注意**: 使用延迟显示列表时,回调在 GPU 线程执行

### 跨上下文纹理

#### `CrossContextTextureFromPixmap`
```cpp
SK_API sk_sp<SkImage> CrossContextTextureFromPixmap(
    GrDirectContext* context,
    const SkPixmap& pixmap,
    bool buildMips,
    bool limitToMaxTextureSize = false);
```
- **功能**: 创建可在多个 GPU 上下文间共享的纹理图像
- **应用场景**: 多线程渲染,GPU 资源共享
- **限制**: 所有上下文必须在同一 GPU 共享组
- **Mipmap 支持**: buildMips 参数控制是否生成 mip 层级
- **尺寸限制**: limitToMaxTextureSize 可自动缩小超大图像

### 压缩纹理支持

#### `TextureFromCompressedTexture`
```cpp
SK_API sk_sp<SkImage> TextureFromCompressedTexture(
    GrRecordingContext* context,
    const GrBackendTexture& backendTexture,
    GrSurfaceOrigin origin,
    SkAlphaType alphaType,
    sk_sp<SkColorSpace> colorSpace,
    TextureReleaseProc textureReleaseProc = nullptr,
    ReleaseContext releaseContext = nullptr);
```
- **功能**: 从已压缩的后端纹理创建图像
- **格式支持**: ETC1, ASTC, BC1 等 GPU 硬件压缩格式
- **Alpha 处理**: 对于不透明格式应使用 kOpaque_SkAlphaType
- **色彩空间**: SRGB 格式应配合线性色彩空间

#### `TextureFromCompressedTextureData`
```cpp
SK_API sk_sp<SkImage> TextureFromCompressedTextureData(
    GrDirectContext* direct,
    sk_sp<SkData> data,
    int width,
    int height,
    SkTextureCompressionType type,
    skgpu::Mipmapped mipmapped = skgpu::Mipmapped::kNo,
    GrProtected isProtected = GrProtected::kNo);
```
- **功能**: 从压缩数据创建 GPU 纹理
- **降级处理**: 如果 GPU 不支持指定压缩格式,自动解压缩
- **能力查询**: 通过 GrRecordingContext::compressedBackendFormat 查询支持
- **DRM 支持**: isProtected 参数启用受保护内存(Vulkan)

### 纹理转换

#### `TextureFromImage`
```cpp
SK_API sk_sp<SkImage> TextureFromImage(
    GrDirectContext* ctx,
    const SkImage* img,
    skgpu::Mipmapped m = skgpu::Mipmapped::kNo,
    skgpu::Budgeted b = skgpu::Budgeted::kYes);
```
- **功能**: 将任意 SkImage 转换为 GPU 纹理支持的图像
- **优化逻辑**: 如果输入已是 GPU 纹理且参数匹配,直接返回原图像
- **预算控制**: Budgeted 参数决定是否计入 GPU 资源预算
- **Mipmap 兼容性**: 不支持 mipmap 的 GPU 会忽略该参数

### YUV 平面图像

#### `TextureFromYUVAPixmaps`
```cpp
SK_API sk_sp<SkImage> TextureFromYUVAPixmaps(
    GrRecordingContext* context,
    const SkYUVAPixmaps& pixmaps,
    skgpu::Mipmapped buildMips = skgpu::Mipmapped::kNo,
    bool limitToMaxTextureSize = false,
    sk_sp<SkColorSpace> imageColorSpace = nullptr);
```
- **功能**: 从 YUV(A) 平面数据创建 GPU 图像
- **平面保持**: 图像保持平面格式,每个平面独立上传为纹理
- **颜色转换**: SkYUVAInfo 指定 YUV 到 RGB 的转换矩阵
- **目标色彩空间**: imageColorSpace 定义最终 RGB 值的色彩空间
- **纹理限制**: 自动处理超出 GPU 最大纹理尺寸的情况

#### `TextureFromYUVATextures`
```cpp
SK_API sk_sp<SkImage> TextureFromYUVATextures(
    GrRecordingContext* context,
    const GrYUVABackendTextures& yuvaTextures,
    sk_sp<SkColorSpace> imageColorSpace,
    TextureReleaseProc textureReleaseProc = nullptr,
    ReleaseContext releaseContext = nullptr);
```
- **功能**: 从已存在的 YUV(A) 后端纹理创建图像
- **生命周期**: 客户端确保纹理在图像生命周期内有效
- **释放回调**: textureReleaseProc 通知所有平面纹理可释放

### 纹理检索与提取

#### `GetBackendTextureFromImage`
```cpp
SK_API bool GetBackendTextureFromImage(
    const SkImage* img,
    GrBackendTexture* outTexture,
    bool flushPendingGrContextIO,
    GrSurfaceOrigin* origin = nullptr);
```
- **功能**: 从 SkImage 获取底层的 Ganesh 后端纹理
- **前提条件**: 图像必须是 Ganesh GPU 纹理支持
- **刷新控制**: flushPendingGrContextIO 决定是否完成延迟 I/O 操作
- **原点信息**: 可选的 origin 参数返回纹理方向

#### `MakeBackendTextureFromImage`
```cpp
SK_API bool MakeBackendTextureFromImage(
    GrDirectContext* context,
    sk_sp<SkImage> image,
    GrBackendTexture* backendTexture,
    BackendTextureReleaseProc* backendTextureReleaseProc);
```
- **功能**: 从任意图像提取或创建后端纹理
- **智能处理**:
  - CPU 图像:上传为纹理
  - GPU 图像(唯一引用):移动纹理所有权
  - GPU 图像(共享引用):复制纹理
- **所有权转移**: 调用者通过 backendTextureReleaseProc 管理纹理生命周期

### 图像操作

#### `SubsetTextureFrom`
```cpp
SK_API sk_sp<SkImage> SubsetTextureFrom(
    GrDirectContext* context,
    const SkImage* img,
    const SkIRect& subset);
```
- **功能**: 创建图像子区域的 GPU 纹理版本
- **验证**: subset 必须非空且在图像边界内
- **上下文匹配**: 源图像如果是 GPU 纹理,必须与提供的 context 匹配

#### `MakeWithFilter`
```cpp
SK_API sk_sp<SkImage> MakeWithFilter(
    GrRecordingContext* context,
    sk_sp<SkImage> src,
    const SkImageFilter* filter,
    const SkIRect& subset,
    const SkIRect& clipBounds,
    SkIRect* outSubset,
    SkIPoint* offset);
```
- **功能**: 在 GPU 上应用图像滤镜,返回滤镜后的图像
- **参数说明**:
  - `subset`: 输入图像的处理区域
  - `clipBounds`: 期望的输出边界
  - `outSubset`: 输出图像在纹理中的有效区域
  - `offset`: 输出图像的平移偏移量
- **动画优化**: GPU 纹理会创建得比需要的稍大,以便重用于不同尺寸的滤镜效果
- **对齐保持**: offset 参数用于保持动画帧之间的对齐

## 内部实现细节

### 纹理所有权模型
Ganesh 支持两种纹理所有权模型:
1. **Adopt(采用)**: Skia 拥有纹理,负责释放
2. **Borrow(借用)**: 客户端拥有纹理,通过回调通知

### DDL(延迟显示列表)兼容性
许多函数在文档中特别注明 DDL 场景下的行为:
- 释放回调在 GPU 线程上执行(录制线程之后)
- 回调时机在 DDL 回放到 Direct Context 之后

### 色彩空间处理
对于 GPU 纹理图像,色彩空间有特殊含义:
- **SRGB 格式纹理**: 应配合线性色彩空间(如 MakeSRGBLinear)
- **线性格式纹理**: 应包含完整的传递函数(如 MakeSRGB)
- 采样后的值根据色彩空间进行解释

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkImage | 核心图像抽象基类 |
| GrRecordingContext | GPU 命令录制上下文 |
| GrDirectContext | 直接 GPU 上下文 |
| GrBackendTexture | 平台无关的后端纹理抽象 |
| GrYUVABackendTextures | YUV 纹理集合 |
| SkYUVAPixmaps | YUV 像素数据 |
| SkPixmap | CPU 像素数据 |
| SkImageFilter | 图像滤镜 |
| GrTypes | Ganesh 核心类型定义 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkCanvas | 在画布上绘制 GPU 图像 |
| SkSurface | 渲染目标管理 |
| 视频解码器 | 使用 YUV 图像 API |
| 图像加载器 | 使用纹理创建 API |

## 设计模式与设计决策

### 工厂函数模式
所有创建函数都是独立的工厂函数,而非类的静态方法,体现了现代 C++ API 设计:
- 避免类名污染
- 支持函数重载
- 便于命名空间组织

### 资源管理策略
采用 RAII 和智能指针(sk_sp)确保资源安全:
- 返回 sk_sp<SkImage> 自动管理引用计数
- 回调函数处理外部资源释放时机

### 向后兼容性
部分函数提供了 legacy 版本:
```cpp
inline bool GetBackendTextureFromImage(...) {
    return MakeBackendTextureFromImage(...);
}
```

## 性能考量

### Mipmap 生成
- buildMips 参数允许延迟 mipmap 生成
- GPU 不支持时自动降级
- 影响纹理采样质量和性能

### 跨上下文共享
CrossContextTextureFromPixmap 创建的纹理可在多个上下文间共享,但:
- 增加内存开销
- 要求上下文在同一共享组
- 适用于多线程渲染场景

### 预算控制
Budgeted 参数控制纹理是否计入 GPU 缓存预算:
- kYes: 可被缓存驱逐
- kNo: 永久保留直到显式释放

## 平台相关说明

### Vulkan 特定
- `isProtected` 参数启用受保护内存(DRM 内容)
- 受保护纹理不能与非保护上下文混用

### GL 特定
- 后端信号量在 GL 后端被忽略
- GL_EXT_texture_storage 可能被 workaround 禁用

## 相关文件
| 文件 | 关系 |
|------|------|
| `include/core/SkImage.h` | 基类定义 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端纹理类型 |
| `src/image/SkImage_Ganesh.cpp` | 实现文件 |
| `include/gpu/ganesh/SkSurfaceGanesh.h` | Surface 对应 API |
| `include/gpu/GpuTypes.h` | GPU 通用类型 |
