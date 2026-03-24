# Image_YUVA_Graphite

> 源文件
> - src/gpu/graphite/Image_YUVA_Graphite.h
> - src/gpu/graphite/Image_YUVA_Graphite.cpp

## 概述

`Image_YUVA` 是 Skia Graphite 渲染引擎中专门用于处理 YUVA（亮度-色度-透明度）格式图像的类。该类继承自 `Image_Base`，负责管理以多平面（planar）格式存储的 YUVA 图像数据，支持各种 YUV 采样方式和色彩空间转换。

YUVA 图像格式在视频处理和图像压缩中广泛使用，因为它可以利用人眼对亮度比色度更敏感的特性进行色度子采样，从而减少存储空间。该类封装了将多个纹理平面组织成完整 YUVA 图像的复杂逻辑。

## 架构位置

```
SkImage (公共 API)
  └── SkImage_Base (基础实现)
      └── Image_Base (Graphite 基础)
          └── Image_YUVA (YUVA 图像实现)
```

在 Graphite 渲染架构中，`Image_YUVA` 位于图像层次结构的叶子节点，与 `Image` 类（普通 RGBA 图像）并列。它依赖 `TextureProxyView` 管理底层纹理资源，并与 `Caps`、`Recorder` 等核心组件协作完成图像操作。

## 主要类与结构体

### Image_YUVA

**核心职责**：
- 管理 YUVA 图像的多个纹理平面
- 处理通道映射和 swizzle 逻辑
- 支持色彩空间转换和图像子集操作

**关键成员**：

```cpp
YUVAProxies fProxies;                    // 4 个通道的纹理代理视图（Y、U、V、A）
SkYUVAInfo fYUVAInfo;                    // YUVA 配置信息（格式、采样方式等）
std::tuple<int, int> fUVSubsampleFactors; // UV 平面的子采样因子
Mipmapped fMipmapped;                    // 聚合的 mipmap 状态
Protected fProtected;                    // 聚合的保护内存状态
```

### YUVAProxies

```cpp
using YUVAProxies = std::array<TextureProxyView, SkYUVAInfo::kYUVAChannelCount>;
```

固定大小的数组（4 个元素），分别对应 Y、U、V、A 通道。每个 `TextureProxyView` 包含纹理代理和 swizzle 信息，用于从底层纹理中提取正确的通道数据。

## 公共 API 函数

### 工厂方法

#### Make

```cpp
static sk_sp<Image_YUVA> Make(
    const Caps* caps,
    const SkYUVAInfo& yuvaInfo,
    SkSpan<TextureProxyView> planes,
    sk_sp<SkColorSpace> imageColorSpace);
```

**功能**：从多个纹理平面创建 YUVA 图像

**核心逻辑**：
1. 验证 `yuvaInfo` 的有效性和平面配置
2. 检查纹理可用性和尺寸匹配
3. 将平面数据重组为通道数据（planes → channels）
4. 根据通道位置生成正确的 swizzle 映射

**关键验证**：
- Y 通道尺寸必须匹配 `yuvaInfo.dimensions()`
- U 和 V 通道尺寸必须相同
- A 通道（如果存在）尺寸必须匹配 Y 通道

#### WrapImages

```cpp
static sk_sp<Image_YUVA> WrapImages(
    const Caps* caps,
    const SkYUVAInfo& yuvaInfo,
    SkSpan<const sk_sp<SkImage>> images,
    sk_sp<SkColorSpace> imageColorSpace);
```

**功能**：包装现有的 Graphite 图像为 YUVA 图像

**特殊行为**：
- 与源图像共享纹理代理
- 继承源图像的设备链接（Device links），保持动态修改同步

### 访问器方法

#### proxyView

```cpp
const TextureProxyView& proxyView(int channelIndex) const;
```

获取指定通道的纹理代理视图。返回的视图已经应用了 swizzle，将相关通道数据映射到 R 分量。

#### textureSize

```cpp
size_t textureSize() const override;
```

计算 YUVA 图像的总 GPU 内存大小，智能去重共享的纹理代理。

### 色彩空间操作

#### onReinterpretColorSpace

```cpp
sk_sp<SkImage> onReinterpretColorSpace(sk_sp<SkColorSpace>) const override;
```

创建使用新色彩空间的图像视图，共享底层纹理和设备链接。

## 内部实现细节

### 通道到平面的映射

YUVA 数据可以以多种方式组织：
- **分离平面**：Y、U、V、A 各占一个纹理
- **打包平面**：如 YUV 在同一纹理的不同通道

实现通过 `SkYUVAInfo::YUVALocations` 描述通道位置，并通过 swizzle 实现通道提取：

```cpp
// 将通道数据映射到 R 分量
Swizzle channelSwizzle = planes[plane].swizzle().selectChannelInR((int)channel);
```

**特殊处理**：
- 检测 alpha-only 格式（`000r` swizzle 或 `kA8` 格式）
- 正确处理 alpha 通道可选的情况

### Alpha 类型推断

```cpp
static SkAlphaType yuva_alpha_type(const SkYUVAInfo& yuvaInfo) {
    return yuvaInfo.hasAlpha() ? kPremul_SkAlphaType : kOpaque_SkAlphaType;
}
```

虽然平面数据是非预乘的，但客户端期望预乘格式，因此存在 alpha 通道时总是返回 `kPremul_SkAlphaType`。

### Mipmap 和保护状态聚合

构造函数遍历所有通道代理，聚合 mipmap 和保护内存状态：

```cpp
for (int i = 0; i < SkYUVAInfo::kYUVAChannelCount; ++i) {
    if (fProxies[i].proxy()->mipmapped() == Mipmapped::kNo) {
        fMipmapped = Mipmapped::kNo;  // 只要有一个不支持就全部不支持
    }
    if (fProxies[i].proxy()->isProtected() == Protected::kYes) {
        fProtected = Protected::kYes;  // 只要有一个需要保护就全部保护
    }
}
```

### 内存大小计算

`textureSize()` 使用智能去重算法避免重复计算共享纹理：

```cpp
for (int i = 0; i < SkYUVAInfo::kYUVAChannelCount; ++i) {
    bool repeat = false;
    for (int j = i - 1; j >= 0; --j) {
        if (fProxies[i].proxy() == fProxies[j].proxy()) {
            repeat = true;
            break;
        }
    }
    if (!repeat) {
        size += /* texture size */;
    }
}
```

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `SkYUVAInfo` | 描述 YUVA 配置（格式、采样、通道位置） |
| `TextureProxyView` | 管理纹理代理和 swizzle |
| `Image_Base` | 提供基础图像功能和设备链接 |
| `Caps` | 查询设备能力（纹理格式支持等） |

### 相关工具类

| 类型 | 用途 |
|------|------|
| `SkYUVAInfo::YUVALocations` | 描述每个 YUVA 通道在哪个平面的哪个分量 |
| `TextureInfoPriv::ChannelMask` | 获取纹理格式的通道掩码 |
| `Swizzle` | 通道重排逻辑 |

## 设计模式与设计决策

### 1. 工厂模式

使用静态工厂方法 `Make` 和 `WrapImages` 而非公共构造函数，允许在创建失败时返回 `nullptr`，并执行复杂的验证逻辑。

### 2. 视图模式

`onReinterpretColorSpace` 创建新的 `Image_YUVA` 对象但共享底层纹理，实现轻量级的色彩空间转换。

### 3. 通道统一访问

所有通道通过统一的数组索引访问（0=Y, 1=U, 2=V, 3=A），简化代码逻辑。Alpha 通道允许为空（null）。

### 4. 延迟实例化

使用 `TextureProxy` 延迟实际纹理分配，支持 `uninstantiatedGpuMemorySize()` 在纹理创建前估算内存。

### 5. 设备链接机制

继承自 `Image_Base` 的设备链接功能，确保动态图像（与 `Device` 共享纹理的图像）在绘制时自动刷新设备的待处理任务。

## 性能考量

### 内存效率

1. **纹理共享**：支持多个通道共享同一纹理（如打包的 YUV 平面），通过 swizzle 区分通道
2. **去重计算**：`textureSize()` 智能检测共享纹理，避免重复计数
3. **子采样支持**：UV 平面可以使用较小分辨率（如 4:2:0 采样），节省内存

### 运行时开销

1. **验证集中**：在 `Make` 方法中一次性完成所有验证，避免运行时检查
2. **预计算信息**：构造时计算并缓存 UV 子采样因子、mipmap 状态等
3. **零拷贝视图**：`onReinterpretColorSpace` 和 `WrapImages` 共享纹理，无额外内存分配

### Swizzle 优化

通过 `selectChannelInR` 将所有通道数据统一映射到 R 分量，简化着色器逻辑：

```cpp
// 所有通道都可以用统一的方式访问：texture.r
channelProxies[i] = planes[plane].replaceSwizzle(channelSwizzle);
```

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/Image_Base_Graphite.h` | YUVA 图像的基类 |
| `src/gpu/graphite/Image_Graphite.h` | 普通 RGBA 图像实现 |
| `src/gpu/graphite/TextureProxyView.h` | 纹理视图管理 |
| `include/core/SkYUVAInfo.h` | YUVA 配置信息定义 |
| `src/gpu/graphite/Caps.h` | 设备能力查询 |
| `src/gpu/graphite/TextureUtils.h` | 纹理工具函数（如 AsView） |
| `src/gpu/graphite/Device.h` | 设备链接支持 |
| `src/gpu/graphite/TextureInfoPriv.h` | 纹理格式私有信息访问 |
