# MtlGraphiteUtils -- Metal 后端工具函数

> 源文件:
> - `src/gpu/graphite/mtl/MtlGraphiteUtils.h`
> - `src/gpu/graphite/mtl/MtlGraphiteUtils.mm`

## 概述

MtlGraphiteUtils 是 Skia Graphite Metal 后端的核心工具模块,提供 MSL 着色器编译、纹理格式转换以及 Metal Context 创建等功能。它是 Metal 后端其他组件的基础依赖,类似于 Vulkan 后端的 `VulkanGraphiteUtils`。

## 架构位置

```
Context (上层接口)
  -> MtlSharedContext (Metal 共享上下文)
    -> MtlGraphiteUtils (工具函数)  <-- 本模块
       -> MTLDevice (Metal 设备)
```

## 主要类与结构体

本模块不定义类,仅包含自由函数和 Metal SDK 版本宏。

### Metal SDK 版本宏

```cpp
#define SKGPU_GRAPHITE_METAL_SDK_VERSION 230/240/300
```
根据编译目标平台（macOS / iOS / tvOS）和 SDK 版本自动设置,用于条件编译。

## 公共 API 函数

### MtlCompileShaderLibrary

```cpp
sk_cfp<id<MTLLibrary>> MtlCompileShaderLibrary(const MtlSharedContext*,
                                               std::string_view label,
                                               std::string_view msl,
                                               ShaderErrorHandler*);
```
将 MSL 着色器源码编译为 `MTLLibrary`:
- 根据平台可用性选择 MSL 语言版本（2.3 / 2.0 / 1.2）
- MSL 2.3 用于支持 Framebuffer Fetch（macOS 11+ / iOS 14+）
- 编译失败时通过 `ShaderErrorHandler` 报告错误
- 成功后设置库标签用于调试

### 纹理格式转换

```cpp
TextureFormat MTLPixelFormatToTextureFormat(MTLPixelFormat);
MTLPixelFormat TextureFormatToMTLPixelFormat(TextureFormat);
```
使用 `MTL_FORMAT_MAPPING` X-Macro 实现双向映射,覆盖约 30 种格式。

### Context 工厂

```cpp
namespace ContextFactory {
std::unique_ptr<Context> MakeMetal(const MtlBackendContext&, const ContextOptions&);
}
```

## 内部实现细节

### 格式常量提取

为避免在映射表中使用 `@available` 检查,部分格式常量从 Metal 头文件中手动提取:

```cpp
MTL_PIXEL_FORMAT(MTLPixelFormatBC1_RGBA_, 130);
MTL_PIXEL_FORMAT(MTLPixelFormatB5G6R5Unorm_, 40);
```

这些常量在 `validate_mtl_pixelformats()` 运行时验证与系统值一致。

### 不支持的格式

Metal 不支持以下 Graphite 格式:
- RGB8 / BGR8 (无 3 通道格式)
- R5_G6_B5 / ARGB4 (仅支持 B5_G6_R5 / ABGR4)
- YUV 平面格式和外部格式

### MSL 版本选择策略

| 平台条件 | MSL 版本 | 关键特性 |
|----------|----------|----------|
| macOS 11+ / iOS 14+ | 2.3 | Framebuffer Fetch |
| macOS 10.13+ / iOS 11+ | 2.0 | array<> 支持 |
| iOS 10+ | 1.2 | 基本 array<> |

## 依赖关系

### 上游依赖
- `Metal/Metal.h` -- Metal 框架
- `src/gpu/graphite/TextureFormat.h` -- 跨后端格式枚举
- `include/gpu/ShaderErrorHandler.h` -- 着色器错误处理

### 下游被依赖
- `MtlGraphicsPipeline` -- 着色器编译
- `MtlComputePipeline` -- 计算着色器编译
- `MtlTexture` -- 格式转换
- `MtlSharedContext` -- Context 创建

## 设计模式与设计决策

1. **X-Macro 格式映射**: 与 Vulkan 后端一致的模式,一份映射表生成正向和反向查找。
2. **常量提取与运行时验证**: 将 `@available` 限定的格式常量以硬编码数值定义,配合运行时 assert 验证,简化了映射表中的可用性检查。
3. **版本渐进**: MSL 版本选择从高到低尝试,确保使用平台支持的最新特性。

## 性能考量

- `MtlCompileShaderLibrary` 使用 `TRACE_EVENT` 追踪编译耗时。
- `NSString` 使用 `initWithBytesNoCopy` 避免不必要的字符串拷贝。
- 格式转换为 O(1) switch 查找。

## 相关文件

- `src/gpu/graphite/mtl/MtlSharedContext.h` -- Metal 共享上下文
- `src/gpu/graphite/mtl/MtlGraphicsPipeline.h` -- Metal 图形管线
- `src/gpu/graphite/mtl/MtlComputePipeline.h` -- Metal 计算管线
- `src/gpu/graphite/TextureFormat.h` -- 跨后端格式定义
- `src/gpu/mtl/MtlUtilsPriv.h` -- 共享 Metal 工具函数
