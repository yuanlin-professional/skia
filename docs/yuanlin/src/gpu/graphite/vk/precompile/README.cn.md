# precompile - Vulkan 预编译着色器支持

## 概述

`src/gpu/graphite/vk/precompile` 目录是 Skia Graphite Vulkan 后端中专门用于着色器预编译（Precompilation）的子模块。预编译机制允许应用程序在实际绘制之前提前编译图形管线，从而避免在渲染关键路径上出现管线编译导致的卡顿（jank）。此目录包含 Vulkan 后端特有的预编译扩展，目前的核心功能是支持 YCbCr（亮度-色度）图像着色器的预编译。

在 Skia 的预编译架构中，客户端通过 `PrecompileShader`、`PrecompileColorFilter`、`PrecompileBlender` 等抽象对象描述可能的绘制组合，然后 Graphite 引擎会枚举这些组合并提前编译对应的图形管线。大多数预编译功能是后端无关的，但 YCbCr 图像处理需要 Vulkan 特有的不可变采样器（Immutable Sampler）信息，因此必须在 Vulkan 后端层提供特定的实现。

此模块的 `PrecompileShaders::VulkanYCbCrImage()` 函数接受 `VulkanYcbcrConversionInfo` 参数，将其转换为 `ImmutableSamplerInfo` 并注入到 `PrecompileImageShader` 中。这使得预编译系统能够为包含 YCbCr 纹理的管线生成正确的描述符集布局和采样器配置，确保预编译的管线与运行时实际使用的管线完全匹配。

## 架构图

```
+----------------------------------------------------------+
|              客户端应用程序                                 |
|  (Android SurfaceFlinger, Video Player 等)               |
+----------------------------------------------------------+
                         |
                         | VulkanYcbcrConversionInfo
                         v
+----------------------------------------------------------+
| PrecompileShaders::VulkanYCbCrImage()                    |
| [src/gpu/graphite/vk/precompile/VulkanPrecompileShader]  |
|                                                          |
|  1. 验证 YcbcrConversionInfo 有效性                       |
|  2. 创建 PrecompileImageShader                           |
|  3. 转换为 ImmutableSamplerInfo                          |
|  4. 包装为 LocalMatrix 着色器                             |
+----------------------------------------------------------+
           |                              |
           v                              v
+------------------------+    +----------------------------+
| PrecompileImageShader  |    | VulkanYcbcrConversion      |
| [Graphite 核心层]       |    | ::ToImmutableSamplerInfo() |
| - ImageShaderFlags     |    | [../VulkanYcbcrConversion] |
| - SkColorInfo 列表      |    +----------------------------+
| - SkTileMode 列表      |
| - ImmutableSamplerInfo |
+------------------------+
           |
           v
+----------------------------------------------------------+
| Graphite 预编译引擎                                       |
| - 枚举着色器/混合/颜色过滤组合                              |
| - 生成 GraphicsPipelineDesc + RenderPassDesc             |
| - 调用 VulkanGraphicsPipeline::Make() 编译管线            |
+----------------------------------------------------------+
           |
           v
+----------------------------------------------------------+
| VkPipeline (缓存在 VkPipelineCache 中)                   |
+----------------------------------------------------------+
```

## 目录结构

```
src/gpu/graphite/vk/precompile/
|-- BUILD.bazel                    # Bazel 构建配置
|-- VulkanPrecompileShader.cpp     # VulkanYCbCrImage 预编译着色器实现
```

公共头文件位于:
```
include/gpu/graphite/vk/precompile/
|-- VulkanPrecompileShader.h       # VulkanYCbCrImage 公共 API 声明
```

## 关键类与函数

### PrecompileShaders::VulkanYCbCrImage()

**声明文件**: `include/gpu/graphite/vk/precompile/VulkanPrecompileShader.h`
**实现文件**: `src/gpu/graphite/vk/precompile/VulkanPrecompileShader.cpp`

这是此模块唯一的公共 API 函数，用于创建一个代表 YCbCr 图像的预编译着色器对象。

```cpp
namespace PrecompileShaders {

SK_API sk_sp<PrecompileShader> VulkanYCbCrImage(
    const skgpu::VulkanYcbcrConversionInfo& YCbCrInfo,
    ImageShaderFlags = ImageShaderFlags::kAll,
    SkSpan<const SkColorInfo> = {},
    SkSpan<const SkTileMode> = { kAllTileModes });

} // namespace PrecompileShaders
```

**参数说明**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `YCbCrInfo` | `VulkanYcbcrConversionInfo` | Vulkan YCbCr 转换配置信息，包含格式、色度滤波器、范围等 |
| `shaderFlags` | `ImageShaderFlags` | 图像着色器标志，默认为 `kAll`，控制生成的着色器变体 |
| `colorInfos` | `SkSpan<const SkColorInfo>` | 可选的颜色信息列表，约束预编译的颜色空间组合 |
| `tileModes` | `SkSpan<const SkTileMode>` | 平铺模式列表，默认包含所有平铺模式 |

**实现逻辑**:

```cpp
sk_sp<PrecompileShader> PrecompileShaders::VulkanYCbCrImage(
        const skgpu::VulkanYcbcrConversionInfo& YCbCrConversionInfo,
        ImageShaderFlags shaderFlags,
        SkSpan<const SkColorInfo> colorInfos,
        SkSpan<const SkTileMode> tileModes) {
    // 1. 验证输入有效性
    if (!YCbCrConversionInfo.isValid()) {
        return nullptr;
    }
    // 2. 创建预编译图像着色器
    sk_sp<PrecompileImageShader> shader = sk_make_sp<PrecompileImageShader>(
            shaderFlags, colorInfos, tileModes, /* raw= */false);
    // 3. 设置不可变采样器信息（Vulkan 特有）
    shader->setImmutableSamplerInfo(
            VulkanYcbcrConversion::ToImmutableSamplerInfo(YCbCrConversionInfo));
    // 4. 包装为 LocalMatrix 着色器以支持矩阵变换
    return PrecompileShaders::LocalMatrix({{ std::move(shader) }});
}
```

### VulkanYcbcrConversion::ToImmutableSamplerInfo()

**文件**: `src/gpu/graphite/vk/VulkanYcbcrConversion.h`

此静态方法将 `VulkanYcbcrConversionInfo`（公共 API 类型）转换为 `ImmutableSamplerInfo`（内部紧凑表示），后者被编码到管线键中以确保预编译和运行时管线匹配。

## 依赖关系

```
VulkanPrecompileShader.cpp
    |
    +-- include/gpu/graphite/vk/precompile/VulkanPrecompileShader.h  (公共 API)
    +-- include/gpu/vk/VulkanTypes.h                                 (Vulkan 类型定义)
    +-- src/gpu/graphite/precompile/PrecompileImageShader.h          (图像着色器预编译基础设施)
    +-- src/gpu/graphite/vk/VulkanYcbcrConversion.h                  (YCbCr 转换与采样器信息)
    +-- include/gpu/graphite/precompile/PrecompileShader.h           (预编译着色器基类)
```

### 依赖层次

| 层次 | 组件 | 说明 |
|------|------|------|
| 公共 API | `PrecompileShaders::VulkanYCbCrImage()` | 客户端直接调用的入口点 |
| Vulkan 后端 | `VulkanYcbcrConversion` | 提供 YCbCr 信息到采样器信息的转换 |
| Graphite 核心 | `PrecompileImageShader` | 后端无关的图像着色器预编译逻辑 |
| Graphite 核心 | `PrecompileShaders::LocalMatrix()` | 通用的本地矩阵包装器 |

## 设计模式分析

### 1. 适配器模式（Adapter Pattern）

`VulkanYCbCrImage()` 函数本质上是一个适配器，将 Vulkan 特有的 `VulkanYcbcrConversionInfo` 适配到后端无关的 `PrecompileImageShader` 接口中。关键转换步骤是 `VulkanYcbcrConversion::ToImmutableSamplerInfo()`，它将 Vulkan 的 YCbCr 采样器信息压缩为一个可嵌入管线键的紧凑格式。

### 2. 组合模式（Composite Pattern）

返回的预编译着色器被包装在 `PrecompileShaders::LocalMatrix()` 中，形成一个着色器组合树。预编译引擎在枚举管线变体时会递归遍历这棵树，为每个叶节点着色器生成对应的管线描述。

### 3. 关注点分离（Separation of Concerns）

预编译架构将三个关注点清晰分离:
- **后端特有信息注入**（本目录）: 将 Vulkan YCbCr 信息转化为不可变采样器配置
- **预编译组合枚举**（Graphite 核心层 `src/gpu/graphite/precompile/`）: 枚举所有可能的着色器/混合/颜色过滤组合
- **管线编译**（Vulkan 后端 `src/gpu/graphite/vk/`）: 实际执行 VkPipeline 创建

## 数据流

### YCbCr 预编译管线的完整数据流

```
1. 客户端提供 YCbCr 配置:
   VulkanYcbcrConversionInfo {
       fFormat, fExternalFormat, fYcbcrModel,
       fYcbcrRange, fXChromaOffset, fYChromaOffset,
       fChromaFilter, fForceExplicitReconstruction, ...
   }

2. 转换为不可变采样器信息:
   VulkanYcbcrConversion::ToImmutableSamplerInfo()
       -> ImmutableSamplerInfo (紧凑的 uint 编码)

3. 注入到预编译图像着色器:
   PrecompileImageShader::setImmutableSamplerInfo(info)
       -> 存储在着色器对象中

4. 预编译引擎枚举组合:
   Precompile::CombinationBuilder
       -> 生成 GraphicsPipelineDesc (包含 ImmutableSamplerInfo)
       -> 生成 RenderPassDesc

5. 管线编译:
   VulkanGraphicsPipeline::Make()
       -> 创建 VkSamplerYcbcrConversion
       -> 创建带有不可变采样器的 VkDescriptorSetLayout
       -> 编译着色器 (SPIR-V)
       -> 创建 VkPipeline
       -> 缓存到 VkPipelineCache

6. 运行时绘制:
   实际 YCbCr 纹理绘制时命中预编译的管线
       -> 无需运行时编译，零卡顿
```

### 典型使用场景

YCbCr 预编译主要用于以下场景:
- **Android 视频播放**: `AHardwareBuffer` 中的视频帧通常使用 YCbCr 格式
- **Android 相机预览**: 相机输出通常为 NV12/NV21 等 YCbCr 格式
- **Android SurfaceFlinger**: 系统合成器需要处理多种 YCbCr 缓冲区格式

## 相关文档与参考

### Skia 预编译系统
- `src/gpu/graphite/precompile/` - Graphite 预编译核心框架
- `include/gpu/graphite/precompile/PrecompileShader.h` - 预编译着色器基类 API
- `include/gpu/graphite/precompile/PrecompileImageShader.h` - 预编译图像着色器
- `tests/graphite/precompile/AndroidYCbCrPrecompileTest.cpp` - YCbCr 预编译测试用例

### Vulkan YCbCr 规范
- [VK_KHR_sampler_ycbcr_conversion](https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VK_KHR_sampler_ycbcr_conversion.html) - Vulkan YCbCr 采样器转换扩展规范
- [VkSamplerYcbcrConversionCreateInfo](https://registry.khronos.org/vulkan/specs/1.3-extensions/man/html/VkSamplerYcbcrConversionCreateInfo.html) - 转换对象创建参数

### 父目录
- `src/gpu/graphite/vk/` - Vulkan 后端主目录，包含 `VulkanYcbcrConversion` 等依赖类
- `src/gpu/graphite/vk/VulkanYcbcrConversion.h` - YCbCr 转换资源类及 `ToImmutableSamplerInfo()` 静态方法
