# include/gpu/graphite/vk/precompile - Vulkan 特有预编译着色器

## 概述

`include/gpu/graphite/vk/precompile` 目录包含 Graphite 渲染引擎中 Vulkan 后端特有的预编译
着色器。目前此目录仅包含一个头文件，提供了 Vulkan YCbCr 图像的预编译着色器支持。

YCbCr（亮度-色度）采样是 Vulkan 的一个扩展功能，主要用于处理来自硬件视频解码器的纹理，
在 Android 平台上尤其重要（处理 `AHardwareBuffer` 中的视频帧）。由于 YCbCr 采样器转换
需要特定的 `VkSamplerYcbcrConversionInfo` 配置，这些信息会影响管线编译，因此需要专门的
预编译支持。

`PrecompileShaders::VulkanYCbCrImage()` 函数允许客户端在已知 YCbCr 转换参数的情况下，
提前为这类图像创建渲染管线。这在视频播放应用中特别有用，因为视频帧的 YCbCr 参数通常
在播放开始前就已知道。

## 架构图

```
include/gpu/graphite/vk/precompile/
    |
    +-- VulkanPrecompileShader.h    <-- Vulkan YCbCr 预编译着色器
            |
            +-- PrecompileShaders::VulkanYCbCrImage()
                    |
                    +-- 需要: VulkanYcbcrConversionInfo
                    +-- 可选: ImageShaderFlags, SkColorInfo, SkTileMode
                    |
                    +--> sk_sp<PrecompileShader>
                            |
                            +--> PaintOptions::setShaders()
                                    |
                                    +--> Precompile()
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `VulkanPrecompileShader.h` | `PrecompileShaders::VulkanYCbCrImage()` 工厂方法 |
| `BUILD.bazel` | Bazel 构建配置 |

## 关键类与函数

### `PrecompileShaders::VulkanYCbCrImage()` 函数

```cpp
namespace skgpu::graphite::PrecompileShaders {
    sk_sp<PrecompileShader> VulkanYCbCrImage(
        const skgpu::VulkanYcbcrConversionInfo& YCbCrInfo,
        ImageShaderFlags flags = ImageShaderFlags::kAll,
        SkSpan<const SkColorInfo> colorInfos = {},
        SkSpan<const SkTileMode> tileModes = { kAllTileModes }
    );
}
```

参数说明：
- `YCbCrInfo`: Vulkan YCbCr 采样器转换的完整配置，包括色度模型、范围、偏移和滤波器等
- `flags`: 图像着色器标志，控制预编译的变体
- `colorInfos`: 可选的颜色信息列表
- `tileModes`: 平铺模式列表，默认为所有支持的平铺模式

### 典型使用流程

```cpp
// 1. 已知视频帧的 YCbCr 参数
skgpu::VulkanYcbcrConversionInfo ycbcrInfo(...);

// 2. 创建预编译着色器
auto shader = PrecompileShaders::VulkanYCbCrImage(ycbcrInfo);

// 3. 设置到 PaintOptions
PaintOptions paintOpts;
paintOpts.setShaders({shader});

// 4. 预编译
RenderPassProperties props;
props.fDstCT = kRGBA_8888_SkColorType;
Precompile(precompileContext, paintOpts, DrawTypeFlags::kSimpleShape, {&props, 1});
```

## 依赖关系

- **上游依赖**: `include/gpu/graphite/precompile/PrecompileShader.h`
- **上游依赖**: `include/gpu/vk/VulkanTypes.h` (VulkanYcbcrConversionInfo)
- **外部依赖**: Vulkan SDK
- **实现代码**: `src/gpu/graphite/vk/precompile/`

## 相关文档与参考

- `include/gpu/graphite/precompile/` - 通用预编译框架
- `include/gpu/graphite/vk/` - Graphite Vulkan 后端
- `include/gpu/vk/VulkanTypes.h` - `VulkanYcbcrConversionInfo` 定义
- Vulkan YCbCr 采样: https://www.khronos.org/registry/vulkan/specs/1.3-extensions/man/html/VK_KHR_sampler_ycbcr_conversion.html
