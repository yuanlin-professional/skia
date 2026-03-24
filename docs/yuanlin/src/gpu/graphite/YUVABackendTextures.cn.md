# YUVABackendTextures

> 源文件: include/gpu/graphite/YUVABackendTextures.h, src/gpu/graphite/YUVABackendTextures.cpp

## 概述

`YUVABackendTextures` 是 Skia Graphite 中用于管理 YUVA 格式平面纹理的核心类。该模块提供两个主要类：`YUVABackendTextureInfo` 用于描述一组存储 YUVA 平面数据的后端纹理信息，`YUVABackendTextures` 用于持有实际的后端纹理。这些类将 YUV 颜色空间的多平面图像数据与 GPU 后端纹理进行桥接，支持视频处理、相机输入等场景中的高效纹理管理。

主要功能包括：
- 管理 YUVA 格式的多平面纹理描述信息
- 验证纹理格式与通道数量的兼容性
- 提供 YUVALocations 布局信息用于着色器访问
- 支持 mipmap 纹理配置

## 架构位置

该模块位于 Skia Graphite GPU 后端架构的纹理管理层：

```
skgpu::graphite
├── Context (上下文管理)
├── Recorder (命令记录)
├── BackendTexture (后端纹理基础类) ← 本模块依赖
├── TextureInfo (纹理信息) ← 本模块使用
├── YUVABackendTextures (本模块)
└── Image/Surface (图像表面层使用本模块)
```

在渲染管线中，该模块位于后端纹理抽象层，为上层图像和表面提供 YUVA 格式的纹理支持。

## 主要类与结构体

### YUVABackendTextureInfo

描述 YUVA 平面纹理配置信息的类。

**继承关系**
- 无继承关系，独立类

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fYUVAInfo` | `SkYUVAInfo` | YUVA 格式描述信息 |
| `fPlaneTextureInfos` | `std::array<TextureInfo, kMaxPlanes>` | 每个平面的纹理信息数组 |
| `fPlaneChannelMasks` | `std::array<uint32_t, kMaxPlanes>` | 每个平面的通道掩码 |
| `fMipmapped` | `Mipmapped` | 是否启用 mipmap |

### YUVABackendTextures

持有实际 YUVA 平面后端纹理的类。

**继承关系**
- 无继承关系，独立类
- 不可拷贝 (deleted copy constructor/assignment)

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fYUVAInfo` | `SkYUVAInfo` | YUVA 格式描述信息 |
| `fPlaneTextures` | `std::array<BackendTexture, kMaxPlanes>` | 实际的后端纹理数组 |
| `fPlaneChannelMasks` | `std::array<uint32_t, kMaxPlanes>` | 每个平面的通道掩码 |

## 公共 API 函数

### YUVABackendTextureInfo 类

**构造函数**
```cpp
YUVABackendTextureInfo(const SkYUVAInfo& yuvaInfo,
                       SkSpan<const TextureInfo> textureInfo,
                       Mipmapped mipmapped);
```
从 YUVAInfo、纹理信息数组和 mipmap 设置构造对象。

**查询接口**
```cpp
const TextureInfo& planeTextureInfo(int i) const;
const SkYUVAInfo& yuvaInfo() const;
int numPlanes() const;
bool isValid() const;
SkYUVAInfo::YUVALocations toYUVALocations() const;
```
提供平面纹理信息、格式信息、有效性验证和位置映射查询。

### YUVABackendTextures 类

**构造函数**
```cpp
YUVABackendTextures(const SkYUVAInfo& yuvaInfo,
                    SkSpan<const BackendTexture> textures);
```
从 YUVAInfo 和后端纹理数组构造对象。

**访问接口**
```cpp
BackendTexture planeTexture(int i) const;
SkSpan<const BackendTexture> planeTextures() const;
int numPlanes() const;
bool isValid() const;
```
提供对平面纹理的访问和查询能力。

## 内部实现细节

### 通道数量验证

通过 `num_channels` 辅助函数将通道掩码转换为通道数：
```cpp
int num_channels(uint32_t ChannelMasks) {
    switch (ChannelMasks) {
        case kRed_SkColorChannelFlag: return 1;
        case kGrayAlpha_SkColorChannelFlags: return 2;
        case kRGB_SkColorChannelFlags: return 3;
        case kRGBA_SkColorChannelFlags: return 4;
        // ...
    }
}
```

### 构造验证逻辑

两个类在构造时都执行严格的验证：

1. **YUVAInfo 有效性检查**：验证 YUVA 格式描述的正确性
2. **平面数量匹配**：确保提供的纹理数量与 YUVAInfo 指定的平面数一致
3. **通道数量验证**：每个平面的纹理必须有足够的通道数
4. **后端一致性**：所有纹理必须来自同一个后端 API (Metal/Vulkan/Dawn)
5. **尺寸验证** (YUVABackendTextures)：验证纹理尺寸与平面尺寸匹配

验证失败时，对象会被重置为无效状态。

### YUVALocations 计算

`toYUVALocations` 方法将内部通道掩码转换为着色器可用的位置信息：
```cpp
auto result = fYUVAInfo.toYUVALocations(fPlaneChannelMasks.data());
```
该位置信息用于告诉 GPU 着色器如何从各个平面采样 YUVA 分量。

### 平面通道掩码获取

通过 `TextureInfoPriv::ChannelMask` 获取每个纹理的通道掩码：
```cpp
fPlaneChannelMasks[i] = TextureInfoPriv::ChannelMask(textureInfo[i]);
```

## 依赖关系

**依赖的模块**

| 模块 | 用途 |
|------|------|
| `SkYUVAInfo` | 提供 YUVA 格式描述 |
| `BackendTexture` | 后端纹理封装 |
| `TextureInfo` | 纹理属性信息 |
| `TextureInfoPriv` | 纹理信息私有访问 |
| `SkYUVAInfoLocation` | YUVA 位置映射 |
| `Caps` | 硬件能力查询 |

**被依赖的模块**

该模块被以下场景使用：
- 视频解码纹理管理
- 相机输入纹理处理
- YUV 格式图像创建
- Image 和 Surface 的 YUVA 支持

## 设计模式与设计决策

### 信息与资源分离模式

设计了两个独立的类：
- `YUVABackendTextureInfo`：轻量级描述信息，可复制
- `YUVABackendTextures`：持有实际纹理资源，不可复制

这种分离使得可以在不持有昂贵资源的情况下传递纹理配置信息。

### 验证前置设计

构造函数执行全面验证，确保对象创建后必然处于有效或明确的无效状态，避免了使用时的额外检查负担。

### 后端无关抽象

通过 `BackendTexture` 和 `TextureInfo` 抽象，支持多种 GPU 后端（Metal、Vulkan、Dawn），而无需在本类中编写后端特定代码。

### 兼容性检查

严格的格式兼容性检查确保纹理通道配置满足 YUVA 格式要求，防止运行时采样错误。

### DEPRECATED 接口保留

保留了带 `Recorder*` 参数的构造函数作为 DEPRECATED 接口，但实际不再需要该参数，保证了 API 向后兼容。

## 性能考量

### 编译时常量

使用 `static constexpr auto kMaxPlanes = SkYUVAInfo::kMaxPlanes` 定义最大平面数，允许编译器优化数组分配。

### 固定大小数组

使用 `std::array` 而非 `std::vector` 存储平面信息，避免动态内存分配开销。

### 验证缓存

构造时完成所有验证，避免每次访问时重复检查。验证失败直接重置为默认状态。

### 断言使用

在调试版本中使用 `SkASSERT` 验证 YUVALocations 的有效性，生产版本不产生额外开销。

### 通道掩码缓存

预先计算并存储每个平面的通道掩码 (`fPlaneChannelMasks`)，避免重复查询。

### 引用传递

查询接口返回 `const` 引用（如 `yuvaInfo()`）而非拷贝，减少数据复制开销。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkYUVAInfo.h` | 依赖 | YUVA 格式描述 |
| `src/core/SkYUVAInfoLocation.h` | 依赖 | YUVA 位置映射实现 |
| `include/gpu/graphite/BackendTexture.h` | 依赖 | 后端纹理定义 |
| `include/gpu/graphite/TextureInfo.h` | 依赖 | 纹理信息定义 |
| `src/gpu/graphite/TextureInfoPriv.h` | 依赖 | 纹理信息私有访问 |
| `src/gpu/graphite/Caps.h` | 依赖 | 硬件能力接口 |
| `include/gpu/graphite/Recorder.h` | 依赖 | 记录器接口（已弃用参数） |
