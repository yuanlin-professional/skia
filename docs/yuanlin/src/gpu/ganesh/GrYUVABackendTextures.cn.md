# GrYUVABackendTextures

> 源文件
> - include/gpu/ganesh/GrYUVABackendTextures.h
> - src/gpu/ganesh/GrYUVABackendTextures.cpp

## 概述

`GrYUVABackendTextures` 是 Skia 图形库中用于管理 YUVA 格式平面纹理的核心组件。该模块提供了两个主要类：`GrYUVABackendTextureInfo` 和 `GrYUVABackendTextures`。前者描述一组后端纹理的配置信息和格式规范,后者则持有实际的后端纹理对象。这些类使得 Skia 能够高效地处理视频图像中常用的 YUVA 色彩空间平面数据,将其与 GPU 后端纹理系统集成。

YUVA 是一种将图像分解为亮度(Y)和色度(U、V)分量的颜色表示方式,常用于视频编码和处理。该模块通过封装后端纹理细节,为上层 API 提供统一的接口来创建、验证和操作 YUVA 平面纹理。

## 架构位置

该模块位于 Skia 的 GPU Ganesh 后端架构中,处于后端纹理抽象层。它直接依赖于 `GrBackendSurface` 和 `SkYUVAInfo` 等核心类型,并被渲染管线的图像解码和纹理上传模块所使用。在 Skia 的 GPU 架构栈中,该模块位于以下位置:

```
应用层 API (SkImage, SkSurface)
    ↓
YUVA 图像处理层 (GrYUVABackendTextures) ← 当前模块
    ↓
后端纹理抽象层 (GrBackendSurface, GrBackendTexture)
    ↓
GPU 后端实现层 (OpenGL, Vulkan, Metal, D3D)
```

## 主要类与结构体

### GrYUVABackendTextureInfo

负责描述一组 YUVA 平面纹理的配置信息。

**继承关系:**
- 无继承关系(独立类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fYUVAInfo` | `SkYUVAInfo` | YUVA 图像的平面配置和色彩空间信息 |
| `fPlaneFormats` | `GrBackendFormat[kMaxPlanes]` | 每个平面的后端纹理格式数组 |
| `fMipmapped` | `skgpu::Mipmapped` | 是否支持多级渐远纹理 |
| `fTextureOrigin` | `GrSurfaceOrigin` | 纹理坐标系原点(上或下) |

### GrYUVABackendTextures

持有实际的 YUVA 平面后端纹理对象。

**继承关系:**
- 无继承关系(独立类)
- 不可拷贝,仅支持移动语义

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fYUVAInfo` | `SkYUVAInfo` | YUVA 图像的平面配置信息 |
| `fTextures` | `std::array<GrBackendTexture, kMaxPlanes>` | 实际后端纹理对象数组 |
| `fTextureOrigin` | `GrSurfaceOrigin` | 纹理坐标系原点 |

## 公共 API 函数

### GrYUVABackendTextureInfo

| 函数签名 | 功能说明 |
|---------|---------|
| `GrYUVABackendTextureInfo(const SkYUVAInfo&, const GrBackendFormat[], skgpu::Mipmapped, GrSurfaceOrigin)` | 构造函数,初始化 YUVA 纹理信息并验证格式兼容性 |
| `bool isValid() const` | 检查配置是否有效 |
| `int numPlanes() const` | 返回平面数量(0-4) |
| `const GrBackendFormat& planeFormat(int i) const` | 获取第 i 个平面的格式 |
| `SkYUVAInfo::YUVALocations toYUVALocations() const` | 转换为 YUVALocations 表示 |
| `SkYUVColorSpace yuvColorSpace() const` | 获取 YUV 色彩空间 |
| `skgpu::Mipmapped mipmapped() const` | 获取 mipmap 设置 |
| `GrSurfaceOrigin textureOrigin() const` | 获取纹理原点 |

### GrYUVABackendTextures

| 函数签名 | 功能说明 |
|---------|---------|
| `GrYUVABackendTextures(const SkYUVAInfo&, const GrBackendTexture[], GrSurfaceOrigin)` | 构造函数,关联实际后端纹理 |
| `bool isValid() const` | 检查纹理对象是否有效 |
| `const std::array<GrBackendTexture, kMaxPlanes>& textures() const` | 获取所有纹理数组 |
| `GrBackendTexture texture(int i) const` | 获取第 i 个平面的纹理 |
| `int numPlanes() const` | 返回平面数量 |
| `SkYUVAInfo::YUVALocations toYUVALocations() const` | 转换为 YUVALocations 表示 |

## 内部实现细节

### 通道数量验证

模块通过 `num_channels()` 辅助函数验证纹理格式的通道数是否满足平面要求:

```cpp
static int num_channels(const GrBackendFormat& format) {
    switch (format.channelMask()) {
        case kRed_SkColorChannelFlag: return 1;
        case kGray_SkColorChannelFlag: return 1;
        case kRG_SkColorChannelFlags: return 2;
        case kRGB_SkColorChannelFlags: return 3;
        case kRGBA_SkColorChannelFlags: return 4;
        default: return 0;
    }
}
```

构造时会验证每个平面的纹理格式通道数是否不少于 `SkYUVAInfo` 要求的通道数,不满足则返回无效状态。

### 格式兼容性检查

在构造 `GrYUVABackendTextureInfo` 时,会执行以下验证:
1. `SkYUVAInfo` 本身必须有效
2. 所有平面的格式必须有效且属于同一后端(OpenGL/Vulkan/Metal 等)
3. 每个平面的通道数必须满足 `numChannelsInPlane(i)` 的要求

在构造 `GrYUVABackendTextures` 时,额外验证:
1. 纹理尺寸必须与 `SkYUVAInfo` 中的平面尺寸匹配
2. 纹理通道数满足要求

### YUVALocations 转换

`toYUVALocations()` 方法将内部表示转换为通道定位信息,指示 Y、U、V、A 各分量在哪个平面的哪个通道中:

```cpp
SkYUVAInfo::YUVALocations GrYUVABackendTextureInfo::toYUVALocations() const {
    uint32_t channelFlags[] = {
        fPlaneFormats[0].channelMask(),
        fPlaneFormats[1].channelMask(),
        fPlaneFormats[2].channelMask(),
        fPlaneFormats[3].channelMask()
    };
    return fYUVAInfo.toYUVALocations(channelFlags);
}
```

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `SkYUVAInfo` | 提供 YUVA 平面配置和色彩空间信息 |
| `GrBackendSurface` | 后端纹理和表面抽象基础 |
| `GrBackendFormat` | 后端纹理格式描述 |
| `GrBackendTexture` | 后端纹理对象封装 |
| `GrTypes` | GPU 类型定义(GrSurfaceOrigin 等) |
| `SkYUVAInfoLocation` | YUVA 通道位置计算 |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| 图像解码器 | 视频帧和 YUVA 图像解码后创建 GPU 纹理 |
| `SkImage` 工厂函数 | 从 YUVA 纹理创建 SkImage 对象 |
| GPU 纹理上传器 | 将 YUVA 数据上传到 GPU |
| 渲染管线 | YUVA 到 RGBA 的色彩空间转换渲染 |

## 设计模式与设计决策

### 信息与资源分离

设计上将配置信息(`GrYUVABackendTextureInfo`)与实际资源(`GrYUVABackendTextures`)分离:
- **Info 类**: 轻量级,可拷贝,用于描述和验证配置
- **Textures 类**: 持有重资源,不可拷贝(仅移动),管理生命周期

这种分离使得配置验证可以在创建实际纹理之前完成,减少资源浪费。

### 移动语义保证唯一所有权

`GrYUVABackendTextures` 删除拷贝构造和拷贝赋值,仅支持移动操作:

```cpp
GrYUVABackendTextures(const GrYUVABackendTextures&) = delete;
GrYUVABackendTextures(GrYUVABackendTextures&&) = default;
```

这确保了后端纹理的唯一所有权,避免意外的资源共享和释放问题。

### 防御性编程

构造函数采用防御性编程策略,任何验证失败都会将对象重置为默认(无效)状态:

```cpp
if (!formats[i].isValid() || formats[i].backend() != formats[0].backend()) {
    *this = {};  // 重置为无效状态
    return;
}
```

这保证了对象状态的一致性,`isValid()` 可以可靠地判断对象是否可用。

### 最大平面数常量

使用 `kMaxPlanes = SkYUVAInfo::kMaxPlanes` 常量(值为 4)定义数组大小,支持最复杂的 YUVA 平面分离方案(Y、U、V、A 各占一个平面)。

## 性能考量

### 栈分配数组

使用 `std::array` 和 C 数组而非动态分配,将平面数据直接存储在对象内部:
- 避免堆分配开销
- 提升缓存局部性
- 平面数量固定且较小(最多 4 个)时性能最优

### 按需验证

通道数量和格式兼容性仅在构造时验证一次,后续通过 `isValid()` 快速检查状态,避免重复验证。

### 通道掩码快速查询

使用 `channelMask()` 位掩码而非字符串比较来判断通道类型,提供 O(1) 的查询性能。

### Debug 模式断言

在 Debug 模式下使用 `SkASSERT` 验证 YUVALocations 的有效性和平面数量一致性,Release 模式下这些检查被优化掉。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkYUVAInfo.h` | 提供 YUVA 平面布局和色彩空间定义 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端纹理和表面基础类型 |
| `src/core/SkYUVAInfoLocation.h` | YUVA 通道位置计算实现 |
| `include/gpu/GpuTypes.h` | GPU 通用类型定义 |
| `include/gpu/ganesh/GrTypes.h` | Ganesh 后端类型定义 |
| `src/image/SkImage_Ganesh.cpp` | 使用该模块创建 YUVA 图像 |
