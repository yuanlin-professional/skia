# Image_Graphite

> 源文件
> - src/gpu/graphite/Image_Graphite.h
> - src/gpu/graphite/Image_Graphite.cpp

## 概述

`Image` 类是 Skia Graphite 渲染引擎中用于表示单一 RGBA 格式 GPU 纹理图像的核心类。该类继承自 `Image_Base`，封装了纹理代理视图（`TextureProxyView`）及其相关的色彩信息，提供图像复制、色彩空间转换、设备包装等功能。

作为 Graphite 中最常用的图像类型，`Image` 负责管理普通的 2D 纹理资源，并支持与渲染设备的动态链接，确保图像在绘制时能正确同步设备的渲染任务。

## 架构位置

```
SkImage (公共 API)
  └── SkImage_Base (基础实现)
      └── Image_Base (Graphite 基础)
          └── Image (RGBA 图像实现)
```

在 Graphite 的图像体系中，`Image` 与 `Image_YUVA` 并列，分别处理 RGBA 和 YUVA 格式的图像。它是最基础的图像类型，直接对应单个 GPU 纹理资源。

## 主要类与结构体

### Image

**核心职责**：
- 封装单个纹理代理视图及其色彩信息
- 提供图像复制功能（支持 blit 和 draw 两种方式）
- 管理与渲染设备的链接关系
- 支持色彩空间重新解释

**关键成员**：

```cpp
TextureProxyView fTextureProxyView;  // 底层纹理代理及 swizzle 信息
```

该类的设计极简，大部分功能继承自 `Image_Base`，仅存储必要的纹理视图信息。

## 公共 API 函数

### 构造函数

```cpp
Image(TextureProxyView view, const SkColorInfo& info);
```

从纹理代理视图和色彩信息创建图像。注意 Graphite 不基于图像 ID 缓存，因此总是请求新的 unique ID（`kNeedNewImageUniqueID`）。

### 工厂方法

#### WrapDevice

```cpp
static sk_sp<Image> WrapDevice(
    sk_sp<Device> device,
    std::optional<SkColorInfo> overrideInfo = std::nullopt);
```

**功能**：包装渲染设备的表面为图像

**核心逻辑**：
1. 从设备获取 `readSurfaceView()`
2. 验证色彩类型与纹理格式的兼容性
3. 处理 alpha 类型转换（允许 Opaque → Premul/Unpremul）
4. 根据 `overrideInfo` 调整 swizzle
5. 建立图像与设备的链接关系

**特殊处理**：
- 支持 `overrideInfo` 改变色彩类型和 alpha 类型
- 保留设备的近似适配（approx backing fit）尺寸
- 自动链接设备，确保绘制时刷新设备任务

#### Copy

```cpp
static sk_sp<Image> Copy(
    Recorder* recorder,
    DrawContext* drawContext,
    const TextureProxyView& srcView,
    const SkColorInfo& srcColorInfo,
    const SkIRect& subset,
    Budgeted budgeted,
    Mipmapped mipmapped,
    SkBackingFit backingFit,
    std::string_view label);
```

**功能**：复制纹理视图到新的可纹理化代理

**复制策略选择**：
1. **Copy-as-blit**（首选）：
   - 源纹理必须支持 `isCopyableSrc`
   - 使用 `CopyTextureToTextureTask` 执行高效的 GPU 复制
2. **Copy-as-draw**（备选）：
   - 源纹理必须 `isTexturable`
   - 创建临时 `Image` 并调用 `CopyAsDraw`

**Mipmap 生成**：
- 如果 `mipmapped == Mipmapped::kYes`，复制后调用 `GenerateMipmaps`
- Mipmap 生成失败会记录警告并返回 `nullptr`

**任务调度**：
- 如果提供 `drawContext`，任务添加到 DrawContext 的任务列表
- 否则添加到 Recorder 的根任务列表

### 属性访问

#### textureProxyView

```cpp
const TextureProxyView& textureProxyView() const;
```

获取底层纹理代理视图的常量引用。

#### textureSize

```cpp
size_t textureSize() const override;
```

返回纹理的 GPU 内存大小：
- 已实例化：调用 `texture()->gpuMemorySize()`
- 未实例化：调用 `proxy()->uninstantiatedGpuMemorySize()`

### 图像操作

#### copyImage

```cpp
sk_sp<Image> copyImage(
    Recorder* recorder,
    const SkIRect& subset,
    Budgeted budgeted,
    Mipmapped mipmapped,
    SkBackingFit backingFit,
    std::string_view label) const override;
```

复制图像的子集，内部调用 `Image::Copy` 静态方法，并先通知设备图像被使用（`notifyInUse`）。

#### onReinterpretColorSpace

```cpp
sk_sp<SkImage> onReinterpretColorSpace(sk_sp<SkColorSpace> newCS) const override;
```

创建具有新色彩空间的图像视图：
- 共享底层 `TextureProxyView`
- 继承设备链接关系
- 零拷贝操作，仅创建新的 `Image` 对象

## 内部实现细节

### 色彩类型兼容性检查

在 `WrapDevice` 中，如果提供 `overrideInfo`，需要验证色彩类型与纹理格式的兼容性：

```cpp
if (!AreColorTypeAndFormatCompatible(overrideInfo->colorType(), format)) {
    return nullptr;
}
```

同时处理 alpha 类型转换规则：
- 原始 alpha 类型必须匹配，或者
- 从 `kOpaque` 转换为 `kPremul` 或 `kUnpremul`

### Swizzle 调整

根据色彩类型的变化，调用 `ReadSwizzleForColorType` 生成新的 swizzle：

```cpp
Swizzle readSwizzle = ReadSwizzleForColorType(overrideInfo->colorType(), format);
view = view.replaceSwizzle(readSwizzle);
```

### Copy-as-blit 流程

1. 调用 `getTextureInfoForSampledCopy` 获取目标纹理信息
2. 创建目标 `TextureProxy`（支持 `SkBackingFit::kApprox`）
3. 创建 `CopyTextureToTextureTask`
4. 如果需要 mipmap，调用 `GenerateMipmaps`

```cpp
auto copyTask = CopyTextureToTextureTask::Make(srcView.refProxy(), subset, dst, {0, 0});
if (drawContext) {
    drawContext->recordDependency(std::move(copyTask));
} else {
    recorder->priv().add(std::move(copyTask));
}
```

### 近似适配尺寸

使用 `SkBackingFit::kApprox` 时，调用 `GetApproxSize` 获取向上取整到2的幂次的尺寸：

```cpp
backingFit == SkBackingFit::kApprox ? GetApproxSize(subset.size()) : subset.size()
```

**限制**：Mipmap 和近似适配不能同时使用（断言检查）。

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `TextureProxyView` | 管理纹理代理和 swizzle |
| `Image_Base` | 提供基础图像功能 |
| `Device` | 设备链接和表面访问 |
| `Recorder` | 资源分配和任务调度 |
| `DrawContext` | 可选的任务上下文 |

### 工具和任务类

| 类型 | 用途 |
|------|------|
| `CopyTextureToTextureTask` | 执行纹理间复制 |
| `GenerateMipmaps` | 生成 mipmap 层级 |
| `CopyAsDraw` | 通过绘制复制图像 |
| `TextureProxy::Make` | 创建纹理代理 |

## 设计模式与设计决策

### 1. 工厂模式

使用 `WrapDevice` 和 `Copy` 静态工厂方法，封装复杂的创建逻辑，允许在失败时返回 `nullptr`。

### 2. 策略模式

复制操作根据源纹理能力自动选择策略：
- **Blit 策略**：高效的 GPU 间复制（首选）
- **Draw 策略**：通过着色器采样复制（备选）

### 3. 视图模式

`onReinterpretColorSpace` 创建轻量级视图对象，共享底层纹理，避免数据复制。

### 4. 延迟实例化

使用 `TextureProxy` 支持延迟分配，可以在纹理创建前估算内存（`uninstantiatedGpuMemorySize`）。

### 5. 设备链接机制

通过 `linkDevice` 建立图像与设备的关系，确保动态图像在使用时自动同步设备任务：

```cpp
sk_sp<Image> image = sk_make_sp<Image>(std::move(view), *overrideInfo);
image->linkDevice(std::move(device));
```

## 性能考量

### 复制性能

1. **优先使用 Blit**：GPU 硬件加速的纹理复制，比 draw-based 复制快得多
2. **条件检查顺序**：先检查 `isCopyableSrc`（快速路径），失败后检查 `isTexturable`（慢速路径）
3. **任务批处理**：支持将任务添加到 `DrawContext`，允许批量提交

### 内存管理

1. **零拷贝视图**：`onReinterpretColorSpace` 和设备包装共享纹理
2. **精确适配控制**：`SkBackingFit::kExact` 避免内存浪费
3. **近似适配优化**：对于临时图像，使用 2 的幂次尺寸可能提高性能

### Mipmap 考量

1. **按需生成**：仅在明确请求 `Mipmapped::kYes` 时生成
2. **失败处理**：Mipmap 生成失败记录警告但不静默忽略
3. **互斥约束**：Mipmap 与近似适配互斥，避免复杂的尺寸计算

### 设备同步开销

`notifyInUse` 调用会遍历链接的设备并可能刷新它们的任务，频繁使用动态图像时可能有性能影响。

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/Image_Base_Graphite.h` | Image 的基类 |
| `src/gpu/graphite/TextureProxyView.h` | 纹理视图封装 |
| `src/gpu/graphite/Device.h` | 渲染设备 |
| `src/gpu/graphite/DrawContext.h` | 绘制上下文 |
| `src/gpu/graphite/Caps.h` | 设备能力查询 |
| `src/gpu/graphite/TextureUtils.h` | 纹理工具函数（CopyAsDraw、GenerateMipmaps） |
| `src/gpu/graphite/task/CopyTask.h` | 纹理复制任务 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `src/gpu/graphite/RecorderPriv.h` | Recorder 私有接口 |
| `src/gpu/graphite/TextureFormat.h` | 纹理格式定义 |
